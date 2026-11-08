from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base, PK_TYPE


class WorkerTask(Base):
    __tablename__ = "worker_tasks"

    task_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    task_code = Column(String(100), unique=True, nullable=False, index=True)
    assigned_worker_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    assigned_by_user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    allocation_id = Column(BigInteger, ForeignKey("order_allocations.allocation_id"), nullable=True)
    dispatch_id = Column(BigInteger, ForeignKey("dispatches.dispatch_id"), nullable=True)
    task_type = Column(String(50), nullable=False)  # PICKING, PACKING, DISPATCH
    priority = Column(String(50), nullable=False, default="NORMAL")  # LOW, NORMAL, HIGH
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    due_at = Column(DateTime(timezone=True), nullable=True)
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    assigned_worker = relationship("User", foreign_keys=[assigned_worker_id], backref="assigned_tasks")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by_user_id], backref="created_tasks")
    allocation = relationship("OrderAllocation", back_populates="tasks")
    dispatch = relationship("Dispatch", back_populates="tasks")
    items = relationship("WorkerTaskItem", back_populates="task", cascade="all, delete-orphan")


class WorkerTaskItem(Base):
    __tablename__ = "worker_task_items"

    task_item_id = Column(PK_TYPE, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("worker_tasks.task_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    completed_quantity = Column(Numeric(12, 2), nullable=False, default=0)

    task = relationship("WorkerTask", back_populates="items")
    product = relationship("Product")
