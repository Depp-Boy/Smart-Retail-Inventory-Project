from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.models.location import Location
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserUpdateRequest,
)
from app.services.audit_service import AuditLogService

VALID_ROLES = {"SHOP_OWNER", "WAREHOUSE_MANAGER", "WAREHOUSE_WORKER", "ADMIN"}


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register(self, req: UserRegisterRequest) -> User:
        role = req.role.upper()
        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{req.role}'. Supported roles are: {', '.join(sorted(VALID_ROLES))}",
            )

        if self.user_repo.get_by_email(req.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A user with email '{req.email}' is already registered.",
            )

        location_id = req.location_id
        if location_id is None and req.location_name and req.location_address:
            loc_type = req.location_type or (
                "SHOP" if role == "SHOP_OWNER" else
                "MAIN_WAREHOUSE" if role in ("WAREHOUSE_MANAGER", "WAREHOUSE_WORKER") else "SHOP"
            )
            new_location = Location(
                location_name=req.location_name.strip(),
                location_type=loc_type.upper(),
                address=req.location_address.strip(),
            )
            self.db.add(new_location)
            self.db.flush()
            location_id = new_location.location_id
        elif location_id is not None:
            location = self.db.query(Location).filter(Location.location_id == location_id).first()
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location with ID {location_id} does not exist.",
                )

        new_user = User(
            name=req.name.strip(),
            email=req.email.lower().strip(),
            password_hash=hash_password(req.password),
            role=role,
            location_id=location_id,
            phone=req.phone.strip() if req.phone else None,
        )
        created_user = self.user_repo.create(new_user)
        AuditLogService.log_event(
            event_type="USER_REGISTERED",
            actor_id=created_user.user_id,
            actor_role=created_user.role,
            entity_type="USER",
            entity_id=created_user.user_id,
            location_id=created_user.location_id,
            details={"role": created_user.role},
        )
        return created_user


    def login(self, req: UserLoginRequest) -> TokenResponse:
        user = self.user_repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            AuditLogService.log_event(
                event_type="AUTH_LOGIN_FAILED",
                actor_id=user.user_id if user else None,
                actor_role=user.role if user else None,
                entity_type="USER",
                entity_id=user.user_id if user else 0,
                location_id=user.location_id if user else None,
                details={"reason": "invalid_credentials"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        settings = get_settings()
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={"sub": str(user.user_id), "email": user.email, "role": user.role},
            expires_delta=expires,
        )
        AuditLogService.log_event(
            event_type="AUTH_LOGIN_SUCCESS",
            actor_id=user.user_id,
            actor_role=user.role,
            entity_type="USER",
            entity_id=user.user_id,
            location_id=user.location_id,
            details={"role": user.role},
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.user_id,
            role=user.role,
        )

    def update_profile(self, user: User, req: UserUpdateRequest) -> User:
        if req.name is not None:
            user.name = req.name.strip()
        if req.phone is not None:
            user.phone = req.phone.strip()
        return self.user_repo.update(user)

    def change_password(self, user: User, req: ChangePasswordRequest) -> None:
        if not verify_password(req.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        user.password_hash = hash_password(req.new_password)
        self.user_repo.update(user)

    @staticmethod
    def seed_demo_accounts(db) -> dict:
        """
        Idempotent: creates demo accounts and sample locations if they do not already exist.
        Strictly for development environment. Never called in production.
        """
        from app.models.location import Location
        from app.models.shop_warehouse import ShopWarehouse
        from app.models.product import Product
        from app.models.inventory import Inventory
        from decimal import Decimal

        created_users = []
        repo = UserRepository(db)

        # 1. Ensure Demo Central Warehouse exists
        demo_wh = db.query(Location).filter(Location.location_name == "Apex Central Logistics Hub").first()
        if not demo_wh:
            demo_wh = db.query(Location).filter(Location.location_type == "MAIN_WAREHOUSE").first()
        if not demo_wh:
            demo_wh = Location(
                location_name="Apex Central Logistics Hub",
                location_type="MAIN_WAREHOUSE",
                address="Industrial Area, Sector 5, Bangalore",
            )
            db.add(demo_wh)
            db.flush()

        # 2. Ensure Demo Retail Shop exists
        demo_shop = db.query(Location).filter(Location.location_name == "Sri Lakshmi Retail Provisions").first()
        if not demo_shop:
            demo_shop = db.query(Location).filter(Location.location_type == "SHOP").first()
        if not demo_shop:
            demo_shop = Location(
                location_name="Sri Lakshmi Retail Provisions",
                location_type="SHOP",
                address="14 5th Main Road, Malleshwaram, Bangalore",
            )
            db.add(demo_shop)
            db.flush()

        # 3. Create demo manager
        if not repo.get_by_email("manager@demo.com"):
            mgr = User(
                name="Rajesh Kumar Verma",
                email="manager@demo.com",
                password_hash=hash_password("demo123"),
                role="WAREHOUSE_MANAGER",
                location_id=demo_wh.location_id,
                phone="+91 98765 43210",
            )
            db.add(mgr)
            created_users.append("manager@demo.com")

        # 4. Create demo shop owner
        if not repo.get_by_email("shop@demo.com"):
            shop_user = User(
                name="Chethan Suhas",
                email="shop@demo.com",
                password_hash=hash_password("demo123"),
                role="SHOP_OWNER",
                location_id=demo_shop.location_id,
                phone="+91 98451 90812",
            )
            db.add(shop_user)
            created_users.append("shop@demo.com")

        db.flush()

        # 5. Create demo worker
        if not repo.get_by_email("worker@demo.com"):
            worker = User(
                name="Suresh Gowda",
                email="worker@demo.com",
                password_hash=hash_password("demo123"),
                role="WAREHOUSE_WORKER",
                location_id=demo_wh.location_id,
                phone="+91 91234 56789",
            )
            db.add(worker)
            created_users.append("worker@demo.com")

        # 6. Ensure Shop-Warehouse association exists
        link = db.query(ShopWarehouse).filter(
            ShopWarehouse.shop_id == demo_shop.location_id,
            ShopWarehouse.warehouse_id == demo_wh.location_id,
        ).first()
        if not link:
            link = ShopWarehouse(
                shop_id=demo_shop.location_id,
                warehouse_id=demo_wh.location_id,
                is_preferred=True,
                priority=1,
            )
            db.add(link)

        # 7. Seed sample products & inventory if none exist
        existing_products_count = db.query(Product).count()
        if existing_products_count == 0:
            sample_prods = [
                Product(product_name="Sona Masoori Rice 25kg", sku="GRN-RICE-25K", category="Grains & Cereals", unit="Bag", price=Decimal("1450.00"), cost_price=Decimal("1200.00"), reorder_threshold=Decimal("20.00")),
                Product(product_name="Organic Toor Dal 1kg", sku="PLS-TOOR-01K", category="Pulses & Lentils", unit="Packet", price=Decimal("165.00"), cost_price=Decimal("130.00"), reorder_threshold=Decimal("30.00")),
                Product(product_name="Pure Refined Sunflower Oil 1L", sku="OIL-SUN-01L", category="Edible Oils", unit="Pouch", price=Decimal("135.00"), cost_price=Decimal("110.00"), reorder_threshold=Decimal("25.00")),
                Product(product_name="Refined White Sugar 1kg", sku="SWT-SUGR-01K", category="Sweeteners", unit="Packet", price=Decimal("48.00"), cost_price=Decimal("38.00"), reorder_threshold=Decimal("50.00")),
                Product(product_name="Whole Wheat Atta 10kg", sku="FLR-WHT-10K", category="Flour & Grains", unit="Bag", price=Decimal("420.00"), cost_price=Decimal("350.00"), reorder_threshold=Decimal("15.00")),
            ]
            for p in sample_prods:
                db.add(p)
            db.flush()

            # Add inventory for warehouse and shop
            for p in sample_prods:
                wh_inv = Inventory(location_id=demo_wh.location_id, product_id=p.product_id, quantity=Decimal("500.00"), reserved_quantity=Decimal("0.00"))
                shop_inv = Inventory(location_id=demo_shop.location_id, product_id=p.product_id, quantity=Decimal("100.00"), reserved_quantity=Decimal("0.00"))
                db.add(wh_inv)
                db.add(shop_inv)

        db.commit()
        return {"seeded": created_users, "message": "Demo environment ready"}

