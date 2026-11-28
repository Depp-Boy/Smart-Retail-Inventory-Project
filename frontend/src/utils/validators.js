export const isValidEmail = (email) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

export const isValidPhone = (phone) =>
  /^[\d\s+\-()]{7,15}$/.test(phone);

export const isStrongPassword = (password) =>
  password.length >= 8 &&
  /[A-Z]/.test(password) &&
  /[a-z]/.test(password) &&
  /\d/.test(password);

export const isRequired = (value) =>
  value !== undefined && value !== null && String(value).trim() !== '';

export const minLength = (value, min) =>
  String(value).length >= min;

export function validateLoginForm({ email, password }) {
  const errors = {};
  if (!isRequired(email)) errors.email = 'Email is required';
  else if (!isValidEmail(email)) errors.email = 'Please enter a valid email address';
  if (!isRequired(password)) errors.password = 'Password is required';
  else if (password.length < 6) errors.password = 'Password must be at least 6 characters';
  return errors;
}

export function validateRegistrationForm(data) {
  const errors = {};
  if (!isRequired(data.fullName)) errors.fullName = 'Full name is required';
  else if (!minLength(data.fullName, 2)) errors.fullName = 'Name must be at least 2 characters';
  if (!isRequired(data.email)) errors.email = 'Email is required';
  else if (!isValidEmail(data.email)) errors.email = 'Please enter a valid email address';
  if (!isRequired(data.phone)) errors.phone = 'Phone number is required';
  else if (!isValidPhone(data.phone)) errors.phone = 'Please enter a valid phone number';
  if (!isRequired(data.password)) errors.password = 'Password is required';
  else if (!isStrongPassword(data.password))
    errors.password = 'Password must be at least 8 characters with uppercase, lowercase, and a number';
  if (!isRequired(data.confirmPassword)) errors.confirmPassword = 'Please confirm your password';
  else if (data.password !== data.confirmPassword) errors.confirmPassword = 'Passwords do not match';
  if (!isRequired(data.shopName)) errors.shopName = 'Shop name is required';
  if (!isRequired(data.shopAddress)) errors.shopAddress = 'Shop address is required';
  return errors;
}
