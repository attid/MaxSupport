from src.domain.models import User, UserRole

def test_user_creation():
    user = User(user_id=123, full_name="Test User")
    assert user.user_id == 123
    assert user.full_name == "Test User"
    assert user.role == UserRole.CLIENT
