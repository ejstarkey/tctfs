"""
TOTP Service - Time-based One-Time Password (2FA) implementation.
"""
import logging
import pyotp
import qrcode
import io
import base64

logger = logging.getLogger(__name__)


class TOTPService:
    """
    Handle TOTP 2FA generation, verification, and QR code creation.
    """
    
    def __init__(self, issuer_name: str = "TCTFS"):
        """
        Initialize TOTP service.
        
        Args:
            issuer_name: Application name for TOTP (shown in authenticator apps)
        """
        self.issuer_name = issuer_name
    
    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret key.
        
        Returns:
            Base32-encoded secret string
        """
        return pyotp.random_base32()
    
    def get_provisioning_uri(self, secret: str, user_email: str) -> str:
        """
        Get provisioning URI for QR code generation.
        
        Args:
            secret: TOTP secret key
            user_email: User's email address (identifier)
        
        Returns:
            Provisioning URI string
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
    
    def generate_qr_code(self, secret: str, user_email: str) -> str:
        """
        Generate QR code image for TOTP setup.
        
        Args:
            secret: TOTP secret key
            user_email: User's email address
        
        Returns:
            Base64-encoded PNG image data
        """
        uri = self.get_provisioning_uri(secret, user_email)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret: str, token: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            secret: TOTP secret key
            token: 6-digit token to verify
            valid_window: Number of time steps to check before/after current (default 1)
        
        Returns:
            True if token is valid
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=valid_window)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    def get_current_token(self, secret: str) -> str:
        """
        Get the current TOTP token (for testing/debugging only).
        
        Args:
            secret: TOTP secret key
        
        Returns:
            Current 6-digit token
        """
        totp = pyotp.TOTP(secret)
        return totp.now()
    
    def get_backup_codes(self, count: int = 10) -> list:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of backup codes to generate
        
        Returns:
            List of backup code strings
        """
        import secrets
        import string
        
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            # Format as XXXX-XXXX
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        
        return codes


# Singleton instance
_totp_service = None

def get_totp_service() -> TOTPService:
    """Get or create the singleton TOTP service."""
    global _totp_service
    if _totp_service is None:
        _totp_service = TOTPService()
    return _totp_service
