from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StaffUserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    is_active: bool = True

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ce champ est obligatoire.")
        return value


class StaffUserCreate(StaffUserBase):
    password: str = Field(min_length=8)
    password_confirmation: str = Field(min_length=8)

    @field_validator("password", "password_confirmation")
    @classmethod
    def validate_password_fields(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
        return value

    @model_validator(mode="after")
    def validate_password_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("La confirmation du mot de passe ne correspond pas.")
        return self


class StaffUserUpdate(StaffUserBase):
    password: str | None = None
    password_confirmation: str | None = None

    @field_validator("password", "password_confirmation")
    @classmethod
    def validate_optional_password_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value:
            return None

        if len(value) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")

        return value

    @model_validator(mode="after")
    def validate_optional_password_match(self):
        if self.password or self.password_confirmation:
            if self.password != self.password_confirmation:
                raise ValueError("La confirmation du mot de passe ne correspond pas.")
        return self


class StaffUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    is_active: bool
    failed_login_attempts: int
    last_login_at: datetime | None
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime