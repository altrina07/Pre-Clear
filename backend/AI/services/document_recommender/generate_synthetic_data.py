"""
Synthetic Data Generator for Document Requirement Training
Generates realistic shipment records with appropriate required documents.
"""
import csv
import random
from pathlib import Path
from typing import List, Tuple

# Product categories and their typical required documents
PRODUCT_MAPPINGS = {
    "batteries": {
        "docs": ["Commercial Invoice", "Packing List", "MSDS", "Battery Certification", "UN 38.3 Test Report"],
        "weight_range": (0.1, 50),
        "value_range": (100, 5000),
    },
    "electronics": {
        "docs": ["Commercial Invoice", "Packing List", "CE Declaration", "Warranty Certificate"],
        "weight_range": (0.5, 20),
        "value_range": (500, 10000),
    },
    "textiles": {
        "docs": ["Commercial Invoice", "Packing List", "Certificate of Origin"],
        "weight_range": (5, 100),
        "value_range": (1000, 20000),
    },
    "food": {
        "docs": ["Commercial Invoice", "Packing List", "Phytosanitary Certificate", "Health Certificate", "FDA Registration"],
        "weight_range": (10, 1000),
        "value_range": (500, 5000),
    },
    "chemicals": {
        "docs": ["Commercial Invoice", "Packing List", "MSDS", "SDS", "Chemical Certificate"],
        "weight_range": (1, 500),
        "value_range": (500, 10000),
    },
    "pharmaceuticals": {
        "docs": ["Commercial Invoice", "Packing List", "FDA Letter", "Distributor License", "GMP Certificate"],
        "weight_range": (0.1, 10),
        "value_range": (1000, 50000),
    },
    "machinery": {
        "docs": ["Commercial Invoice", "Packing List", "Inspection Certificate", "Warranty"],
        "weight_range": (50, 1000),
        "value_range": (5000, 100000),
    },
}

COUNTRIES = ["US", "CN", "IN", "DE", "MX", "BR", "JP", "KR", "IT", "FR", "GB", "CA", "AU", "SG"]
PACKAGE_TYPES = ["Box", "Pallet", "Container", "Drum", "Case"]
SERVICE_LEVELS = ["Standard", "Express", "Economy", "Freight"]
SHIPMENT_TYPES = ["Domestic", "International"]
HS_CODES = {
    "batteries": ["8507", "8506"],
    "electronics": ["8471", "8504", "8534", "9504"],
    "textiles": ["6201", "6202", "6203", "6204"],
    "food": ["0201", "0202", "0207", "0401", "0402"],
    "chemicals": ["2801", "2802", "2805", "2806", "3002"],
    "pharmaceuticals": ["3004", "3005"],
    "machinery": ["8401", "8402", "8403", "8407"],
}


def generate_synthetic_documents(
    num_records: int = 1000, seed: int = 42, output_file: str = None
) -> List[dict]:
    """
    Generate synthetic shipment records with document requirements.
    
    Args:
        num_records: Number of synthetic records to generate
        seed: Random seed for reproducibility
        output_file: Optional path to save CSV file
    
    Returns:
        List of dictionaries representing shipment records
    """
    random.seed(seed)
    records = []
    
    product_categories = list(PRODUCT_MAPPINGS.keys())
    
    for i in range(num_records):
        category = random.choice(product_categories)
        category_info = PRODUCT_MAPPINGS[category]
        
        # Select HS code from category options
        hs_code = random.choice(HS_CODES.get(category, ["9999"]))
        
        # Build record
        record = {
            "product_name": f"{category.title()} Product {i+1}",
            "category": category,
            "product_description": f"High-quality {category} product for industrial use",
            "hs_code": hs_code,
            "origin_country": random.choice(COUNTRIES),
            "destination_country": random.choice(COUNTRIES),
            "package_type": random.choice(PACKAGE_TYPES),
            "weight": round(random.uniform(*category_info["weight_range"]), 2),
            "declared_value": round(random.uniform(*category_info["value_range"]), 2),
            "shipment_type": random.choice(SHIPMENT_TYPES),
            "service_level": random.choice(SERVICE_LEVELS),
            "required_documents": ", ".join(category_info["docs"]),
        }
        
        # Add conditional rules
        if record["weight"] > 100:
            if "Inspection Certificate" not in record["required_documents"]:
                record["required_documents"] += ", Inspection Certificate"
        
        if record["declared_value"] > 10000 and "Broker Review" not in record["required_documents"]:
            record["required_documents"] += ", Broker Review"
        
        if record["shipment_type"] == "International" and "Certificate of Origin" not in record["required_documents"]:
            record["required_documents"] += ", Certificate of Origin"
        
        records.append(record)
    
    # Save to CSV if path provided
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", newline="") as f:
            fieldnames = [
                "product_name", "category", "product_description", "hs_code",
                "origin_country", "destination_country", "package_type", "weight",
                "declared_value", "shipment_type", "service_level", "required_documents"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        print(f"✓ Generated {num_records} synthetic records to {output_file}")
    
    return records


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic training data for document recommender")
    parser.add_argument("--rows", type=int, default=1000, help="Number of records to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, help="Output CSV file path")
    
    args = parser.parse_args()
    
    output_path = args.output or str(Path(__file__).parent / "data" / "synthetic_documents_data.csv")
    generate_synthetic_documents(num_records=args.rows, seed=args.seed, output_file=output_path)
