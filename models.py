from typing import List, Optional

from pydantic import BaseModel, Field


class ResalePrices(BaseModel):
    bricklink: Optional[float] = None
    brickowl: Optional[float] = None
    brickeconomy: Optional[float] = None


class LegoSetReport(BaseModel):
    set_number: str
    set_name: Optional[str] = None
    theme: Optional[str] = None
    retail_price_usd: Optional[float] = Field(
        None,
        description="Original MSRP in USD, sourced from LEGO.com",
    )
    piece_count: Optional[int] = None
    availability_status: Optional[str] = Field(
        None,
        description="in production / retired / exclusive",
    )
    resale_new: ResalePrices = Field(default_factory=ResalePrices)
    resale_used: ResalePrices = Field(default_factory=ResalePrices)
    growth_percent_since_release: Optional[float] = None
    retirement_date: Optional[str] = None
    sources_missing: list[str] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    verdict: str = Field(
        ...,
        description="1-3 sentence plain-language synthesis, not a restatement of numbers",
    )


class LegoSite(BaseModel):
    product_title: str
    price: float
    piece_count: int
    recommended_age: str
    average_rating: float
    summary: str
    image_urls: Optional[List[str]] = Field( max_length=8, default_factory=list)
    recommended_products: Optional[List[dict]] = Field(
        description="Top 3 recommended products with title and price",
        default_factory=dict
    )

class BrickEconomy(BaseModel):
    set_number: str = Field(description="The official set number, e.g., '75415-1'")
    name: str = Field(description="The full name of the LEGO set")
    theme: str
    subtheme: str
    release_year: int
    retail_price: float = Field(description="The official retail price as a float")
    piece_count: int
    retirement_forecast: Optional[str] = Field(description="Projected retirement timeframe")
    expected_value_post_retirement: Optional[str] = Field(None, description="Estimated value range after retirement")