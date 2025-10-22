"""
Password Service - Password hashing and validation with bcrypt.
"""
import logging
import bcrypt
import re

logger = logging.getLogger(__name__)


class PasswordService:
    """
    Handle password hashing, verification, and policy enforcement.
    """
    
    # Password policy requirements
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
        
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain text password to verify
            hashed: Stored password hash
        
        Returns:
            True if password matches hash
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def validate_password_policy(self, password: str) -> tuple:
        """
        Validate password against policy requirements.
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        if len(password) < self.MIN_LENGTH:
            return False, f"Password must be at least {self.MIN_LENGTH} characters long"
        
        if self.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if self.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, None
    
    def generate_random_password(self, length: int = 16) -> str:
        """
        Generate a random secure password.
        
        Args:
            length: Password length (default 16)
        
        Returns:
            Random password string
        """
        import secrets
        import string
        
        # Ensure we have at least one of each required character type
        password = []
        
        if self.REQUIRE_UPPERCASE:
            password.append(secrets.choice(string.ascii_uppercase))
        if self.REQUIRE_LOWERCASE:
            password.append(secrets.choice(string.ascii_lowercase))
        if self.REQUIRE_DIGIT:
            password.append(secrets.choice(string.digits))
        if self.REQUIRE_SPECIAL:
            password.append(secrets.choice('!@#$%^&*()'))
        
        # Fill the rest with random characters
        all_chars = string.ascii_letters + string.digits + '!@#$%^&*()'
        remaining_length = length - len(password)
        password.extend(secrets.choice(all_chars) for _ in range(remaining_length))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)


# Singleton instance
_password_service = None

def get_password_service() -> PasswordService:
    """Get or create the singleton password service."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service
