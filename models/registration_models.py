from pydantic import BaseModel, Field, EmailStr, HttpUrl, validator, model_validator
from typing import Optional, List, Dict
from datetime import datetime

class CompanyDetails(BaseModel):
    companyName: str
    companyType: str
    dateOfEstablishment: datetime
    country: str
    state: str
    city: str
    address: str
    websiteUrl: Optional[str] = None

class BusinessCapabilities(BaseModel):
    businessRoles: str
    industrySectors: str
    productServiceKeywords: str
    technicalCapabilities: Optional[str] = None
    certifications: Optional[str] = None
    hasNoCertifications: bool = False

    @model_validator(mode="after")
    def check_certifications(self):
        if not self.hasNoCertifications and not self.certifications:
            raise ValueError("Certifications are required if hasNoCertifications is false")
        if self.hasNoCertifications and self.certifications:
            raise ValueError("Cannot have certifications if hasNoCertifications is true")
        return self

class TurnoverEntry(BaseModel):
    financialYear: str
    amount: str

class FinancialLegalInfo(BaseModel):
    hasPan: bool
    hasGstin: bool
    hasMsmeUdyam: bool
    hasNsic: bool
    annualTurnovers: List[TurnoverEntry]
    netWorthAmount: str
    netWorthCurrency: str
    isBlacklistedOrLitigation: bool
    blacklistedDetails: Optional[str] = None

    @validator("annualTurnovers")
    def validate_turnovers(cls, v):
        if len(v) < 1:
            raise ValueError("At least one turnover entry is required")
        # Check if first entry (latest year) has amount
        if not v[0].amount or v[0].amount.strip() == "":
            raise ValueError("Latest financial year turnover is required")
        return v

    @model_validator(mode="after")
    def check_blacklisting(self):
        if self.isBlacklistedOrLitigation and not self.blacklistedDetails:
            raise ValueError("Blacklisting details required when isBlacklistedOrLitigation is true")
        return self

class TenderExperience(BaseModel):
    suppliedToGovtPsus: bool
    hasPastClients: bool
    pastClients: Optional[str] = None
    highestOrderValueFulfilled: float
    tenderTypesHandled: str

    @model_validator(mode="after")
    def check_past_clients(self):
        if self.hasPastClients and not self.pastClients:
            raise ValueError("Past clients details required when hasPastClients is true")
        return self

class GeographicDigitalReach(BaseModel):
    operatesInMultipleStates: bool
    operationalStates: Optional[str] = None
    exportsToOtherCountries: bool
    countriesServed: Optional[str] = None
    hasImportLicense: bool
    hasExportLicense: bool
    registeredOnPortals: bool
    hasDigitalSignature: bool
    preferredTenderLanguages: str

    @model_validator(mode="after")
    def check_geographic_details(self):
        if self.operatesInMultipleStates and not self.operationalStates:
            raise ValueError("Operational states required when operatesInMultipleStates is true")
        if self.exportsToOtherCountries and not self.countriesServed:
            raise ValueError("Countries served required when exportsToOtherCountries is true")
        return self

class TermsAndConditions(BaseModel):
    acknowledgmentOfTenderMatching: bool
    accuracyOfSharedCompanyProfile: bool
    noResponsibilityForTenderOutcomes: bool
    nonDisclosureAndLimitedUse: bool

    @model_validator(mode="after")
    def all_terms_accepted(self):
        for field, value in self.__dict__.items():
            if not value:
                raise ValueError(f"All terms must be accepted: {field}")
        return self

class DeclarationsUploads(BaseModel):
    infoConfirmed: bool

    @validator("infoConfirmed")
    def must_confirm(cls, v):
        if not v:
            raise ValueError("Information must be confirmed")
        return v

class RegistrationRequest(BaseModel):
    companyDetails: CompanyDetails
    businessCapabilities: BusinessCapabilities
    financialLegalInfo: FinancialLegalInfo
    tenderExperience: TenderExperience
    geographicDigitalReach: GeographicDigitalReach
    termsAndConditions: TermsAndConditions
    declarationsUploads: DeclarationsUploads