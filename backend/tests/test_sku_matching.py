import sys
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models import Base, SKU, SKUAlias
from app.services.inventory_service import InventoryService


def _setup_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Fix integer types for SQLite
    for model in [SKU, SKUAlias]:
        for column in model.__table__.columns:
            if hasattr(column.type, '__class__') and 'BigInteger' in str(column.type.__class__):
                column.type = Integer()
    
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_exact_sku_name_matching():
    """Test exact SKU name matching"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create test SKUs
        sku1 = SKU(name="Apple iPhone 14 Pro", tracks_serial_numbers=True)
        sku2 = SKU(name="Samsung Galaxy S23", tracks_serial_numbers=True) 
        sku3 = SKU(name="Xiaomi Redmi Note 12", tracks_serial_numbers=False)
        
        session.add_all([sku1, sku2, sku3])
        session.commit()
        
        service = InventoryService(session)
        
        # Test exact matches
        matches = service.resolve_sku_name("Apple iPhone 14 Pro")
        assert len(matches) >= 1
        exact_match = next((m for m in matches if m["match_type"] == "exact"), None)
        assert exact_match is not None
        assert exact_match["sku_name"] == "Apple iPhone 14 Pro"
        assert exact_match["confidence"] == 1.0
        
        matches = service.resolve_sku_name("Samsung Galaxy S23")
        exact_match = next((m for m in matches if m["match_type"] == "exact"), None)
        assert exact_match is not None
        assert exact_match["sku_name"] == "Samsung Galaxy S23"


def test_alias_sku_matching():
    """Test SKU matching via aliases"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create SKU with aliases
        sku = SKU(name="MacBook Pro 13-inch M2", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()
        session.refresh(sku)
        
        # Create aliases
        alias1 = SKUAlias(sku_id=sku.id, alias="MacBook Pro 13")
        alias2 = SKUAlias(sku_id=sku.id, alias="MBP 13 M2")
        alias3 = SKUAlias(sku_id=sku.id, alias="Apple Laptop 13")
        
        session.add_all([alias1, alias2, alias3])
        session.commit()
        
        service = InventoryService(session)
        
        # Test alias matches
        matches = service.resolve_sku_name("MacBook Pro 13")
        alias_match = next((m for m in matches if m["match_type"] == "alias"), None)
        assert alias_match is not None
        assert alias_match["sku_name"] == "MacBook Pro 13-inch M2"
        assert alias_match["confidence"] == 1.0
        
        matches = service.resolve_sku_name("MBP 13 M2")
        alias_match = next((m for m in matches if m["match_type"] == "alias"), None)
        assert alias_match is not None
        assert alias_match["sku_name"] == "MacBook Pro 13-inch M2"


def test_fuzzy_sku_matching():
    """Test fuzzy SKU matching with similarity threshold"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create test SKUs with similar names
        sku1 = SKU(name="Dell XPS 13 Laptop", tracks_serial_numbers=True)
        sku2 = SKU(name="HP Pavilion 15 Gaming", tracks_serial_numbers=True)
        sku3 = SKU(name="Lenovo ThinkPad X1 Carbon", tracks_serial_numbers=True)
        
        session.add_all([sku1, sku2, sku3])
        session.commit()
        
        service = InventoryService(session)
        
        # Test fuzzy matching with high threshold
        matches = service.resolve_sku_name("Dell XPS 13", threshold=0.8)
        assert len(matches) > 0
        
        fuzzy_match = next((m for m in matches if m["match_type"] == "fuzzy"), None)
        assert fuzzy_match is not None
        assert "Dell XPS 13" in fuzzy_match["sku_name"]
        assert fuzzy_match["confidence"] >= 0.8
        
        # Test partial matching
        matches = service.resolve_sku_name("XPS Laptop", threshold=0.6)
        fuzzy_matches = [m for m in matches if m["match_type"] == "fuzzy"]
        assert len(fuzzy_matches) > 0


def test_sku_matching_threshold():
    """Test SKU matching respects confidence threshold"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        sku = SKU(name="Very Specific Product Name With Many Words", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()
        
        service = InventoryService(session)
        
        # Test with high threshold - should not match unrelated terms
        matches = service.resolve_sku_name("Completely Different Product", threshold=0.9)
        fuzzy_matches = [m for m in matches if m["match_type"] == "fuzzy" and m["confidence"] >= 0.9]
        assert len(fuzzy_matches) == 0
        
        # Test with lower threshold - might find some matches
        matches = service.resolve_sku_name("Product Name", threshold=0.5)
        fuzzy_matches = [m for m in matches if m["match_type"] == "fuzzy" and m["confidence"] >= 0.5]
        assert len(fuzzy_matches) > 0


def test_multiple_match_types():
    """Test when query matches multiple SKUs with different match types"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create SKUs with overlapping terms
        sku1 = SKU(name="iPhone 14 Pro", tracks_serial_numbers=True)
        sku2 = SKU(name="iPhone 14 Pro Max", tracks_serial_numbers=True) 
        sku3 = SKU(name="Apple iPhone 14", tracks_serial_numbers=True)
        
        session.add_all([sku1, sku2, sku3])
        session.commit()
        session.refresh(sku1)
        
        # Add alias
        alias = SKUAlias(sku_id=sku1.id, alias="iPhone Pro")
        session.add(alias)
        session.commit()
        
        service = InventoryService(session)
        
        # Search for "iPhone Pro" - should match alias (exact) and fuzzy matches
        matches = service.resolve_sku_name("iPhone Pro", threshold=0.7)
        
        # Should have alias match with highest confidence
        alias_matches = [m for m in matches if m["match_type"] == "alias"]
        assert len(alias_matches) >= 1
        assert alias_matches[0]["confidence"] == 1.0
        
        # Should also have fuzzy matches
        fuzzy_matches = [m for m in matches if m["match_type"] == "fuzzy"]
        assert len(fuzzy_matches) >= 1
        
        # Results should be sorted by confidence (highest first)
        confidences = [m["confidence"] for m in matches]
        assert confidences == sorted(confidences, reverse=True)


def test_sku_matching_case_insensitive():
    """Test that SKU matching is case insensitive"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        sku = SKU(name="MacBook Air M2", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()
        session.refresh(sku)
        
        alias = SKUAlias(sku_id=sku.id, alias="macbook air")
        session.add(alias)
        session.commit()
        
        service = InventoryService(session)
        
        # Test various case combinations
        test_queries = [
            "MACBOOK AIR M2",
            "macbook air m2", 
            "MacBook Air M2",
            "Macbook Air M2"
        ]
        
        for query in test_queries:
            matches = service.resolve_sku_name(query)
            exact_match = next((m for m in matches if m["match_type"] == "exact"), None)
            assert exact_match is not None, f"Failed to find exact match for: {query}"
            assert exact_match["confidence"] == 1.0


def test_sku_suggestions():
    """Test SKU name suggestions for partial matches"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        # Create SKUs with common prefixes
        skus = [
            SKU(name="iPhone 14 Pro 128GB", tracks_serial_numbers=True),
            SKU(name="iPhone 14 Pro 256GB", tracks_serial_numbers=True),
            SKU(name="iPhone 14 Pro 512GB", tracks_serial_numbers=True),
            SKU(name="iPhone 14 Pro Max 128GB", tracks_serial_numbers=True)
        ]
        session.add_all(skus)
        session.commit()
        
        service = InventoryService(session)
        
        # Search for partial match
        result = service.resolve_sku_name("iPhone 14 Pro", threshold=0.7)
        
        # Should have suggestions for related products
        suggestions = service.get_sku_suggestions("iPhone 14 Pro")
        assert len(suggestions) > 0
        
        # Suggestions should include variations
        suggestion_text = " ".join(suggestions).lower()
        assert "128gb" in suggestion_text or "256gb" in suggestion_text or "512gb" in suggestion_text


def test_empty_query_handling():
    """Test handling of empty or invalid queries"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        service = InventoryService(session)
        
        # Test empty string
        matches = service.resolve_sku_name("")
        assert len(matches) == 0
        
        # Test whitespace only
        matches = service.resolve_sku_name("   ")
        assert len(matches) == 0
        
        # Test None (should not crash)
        try:
            matches = service.resolve_sku_name(None)
            assert len(matches) == 0
        except (TypeError, AttributeError):
            # Expected behavior for None input
            pass


@patch('rapidfuzz.fuzz.ratio')
def test_fuzzy_matching_with_mock(mock_ratio):
    """Test fuzzy matching logic with mocked similarity scores"""
    SessionLocal = _setup_db()
    
    with SessionLocal() as session:
        sku = SKU(name="Test Product For Fuzzy", tracks_serial_numbers=True)
        session.add(sku)
        session.commit()
        
        # Mock the similarity function to return specific scores
        mock_ratio.return_value = 85  # 85% similarity
        
        service = InventoryService(session)
        matches = service.resolve_sku_name("Test Product Fuzzy", threshold=0.8)
        
        fuzzy_matches = [m for m in matches if m["match_type"] == "fuzzy"]
        assert len(fuzzy_matches) == 1
        assert fuzzy_matches[0]["confidence"] == 0.85


if __name__ == "__main__":
    test_exact_sku_name_matching()
    test_alias_sku_matching()
    test_fuzzy_sku_matching()
    test_sku_matching_threshold()
    test_multiple_match_types()
    test_sku_matching_case_insensitive()
    test_sku_suggestions()
    test_empty_query_handling()
    test_fuzzy_matching_with_mock()
    print("All SKU matching tests passed!")