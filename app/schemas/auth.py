from pydantic import BaseModel, field_validator

class LoginForm(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()

        if not value:
            raise ValueError("L'adresse e-mail est obligatoire.")

        if "@" not in value:
            raise ValueError("L'adresse e-mail doit contenir @.")

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Le mot de passe est obligatoire.")

        return value