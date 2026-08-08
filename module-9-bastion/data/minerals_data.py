"""
Reference dataset for Bastion — Critical Minerals Supply Chain module.

Production-share figures are illustrative approximations built from
public USGS Mineral Commodity Summaries-style concentration patterns.
They are NOT pulled from a live feed. See ADR-001 for the honesty
boundary on this data.
"""

MINERALS = [
    {
        "symbol": "Nd",
        "name": "Neodymium",
        "category": "Rare Earth Element",
        "physical_properties": {
            "color": "Silvery-white, tarnishes yellow in air",
            "density_g_cm3": 7.01,
            "melting_point_c": 1021,
            "hardness_mohs": None,
        },
        "chemical_properties": {
            "formula": "Nd",
            "reactivity": "Reacts slowly with air, rapidly with water",
            "crystal_structure": "Hexagonal / double hexagonal close-packed",
        },
        "applications": ["Magnetics", "Aerospace", "Medical (MRI magnets)"],
        "producing_countries": {"China": 0.85, "USA": 0.06, "Myanmar": 0.05, "Other": 0.04},
        "criticality": "High",
        "substitutability": "Low",
    },
    {
        "symbol": "Dy",
        "name": "Dysprosium",
        "category": "Rare Earth Element",
        "physical_properties": {
            "color": "Silvery-white",
            "density_g_cm3": 8.54,
            "melting_point_c": 1412,
            "hardness_mohs": None,
        },
        "chemical_properties": {
            "formula": "Dy",
            "reactivity": "Tarnishes slowly in air",
            "crystal_structure": "Hexagonal close-packed",
        },
        "applications": ["Magnetics", "Aerospace", "Lasers"],
        "producing_countries": {"China": 0.90, "Myanmar": 0.07, "Other": 0.03},
        "criticality": "High",
        "substitutability": "Very Low",
    },
    {
        "symbol": "Ga",
        "name": "Gallium",
        "category": "Specialty Metal",
        "physical_properties": {
            "color": "Silvery",
            "density_g_cm3": 5.91,
            "melting_point_c": 29.8,
            "hardness_mohs": 1.5,
        },
        "chemical_properties": {
            "formula": "Ga",
            "reactivity": "Reacts with most acids, forms GaAs semiconductors",
            "crystal_structure": "Orthorhombic",
        },
        "applications": ["Computer Hardware", "Lasers", "Aerospace (RF chips)"],
        "producing_countries": {"China": 0.94, "Other": 0.06},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Ge",
        "name": "Germanium",
        "category": "Specialty Metal",
        "physical_properties": {
            "color": "Grayish-white",
            "density_g_cm3": 5.32,
            "melting_point_c": 938,
            "hardness_mohs": 6.0,
        },
        "chemical_properties": {
            "formula": "Ge",
            "reactivity": "Stable in air at room temperature",
            "crystal_structure": "Diamond cubic",
        },
        "applications": ["Computer Hardware", "Catalysts", "Medical (infrared optics)"],
        "producing_countries": {"China": 0.68, "Russia": 0.03, "Other": 0.29},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Co",
        "name": "Cobalt",
        "category": "Battery Metal",
        "physical_properties": {
            "color": "Silvery-blue",
            "density_g_cm3": 8.90,
            "melting_point_c": 1495,
            "hardness_mohs": 5.0,
        },
        "chemical_properties": {
            "formula": "Co",
            "reactivity": "Slow oxidation in air",
            "crystal_structure": "Hexagonal close-packed",
        },
        "applications": ["Metal Alloys", "Batteries", "Catalysts"],
        "producing_countries": {"DRC": 0.70, "Indonesia": 0.06, "Other": 0.24},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Li",
        "name": "Lithium",
        "category": "Battery Metal",
        "physical_properties": {
            "color": "Silvery-white",
            "density_g_cm3": 0.534,
            "melting_point_c": 180.5,
            "hardness_mohs": 0.6,
        },
        "chemical_properties": {
            "formula": "Li",
            "reactivity": "Highly reactive, reacts with water",
            "crystal_structure": "Body-centered cubic",
        },
        "applications": ["Batteries", "Catalysts", "Aerospace (alloys)"],
        "producing_countries": {"Australia": 0.47, "Chile": 0.24, "China": 0.13, "Other": 0.16},
        "criticality": "High",
        "substitutability": "Low",
    },
    {
        "symbol": "Pt",
        "name": "Platinum",
        "category": "Platinum Group Metal",
        "physical_properties": {
            "color": "Silvery-white",
            "density_g_cm3": 21.45,
            "melting_point_c": 1768,
            "hardness_mohs": 4.3,
        },
        "chemical_properties": {
            "formula": "Pt",
            "reactivity": "Highly inert, resists oxidation and acids",
            "crystal_structure": "Face-centered cubic",
        },
        "applications": ["Catalysts", "Medical (implants)", "Computer Hardware"],
        "producing_countries": {"South Africa": 0.71, "Russia": 0.12, "Other": 0.17},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Pd",
        "name": "Palladium",
        "category": "Platinum Group Metal",
        "physical_properties": {
            "color": "Silvery-white",
            "density_g_cm3": 12.02,
            "melting_point_c": 1555,
            "hardness_mohs": 4.75,
        },
        "chemical_properties": {
            "formula": "Pd",
            "reactivity": "Absorbs hydrogen readily, resists corrosion",
            "crystal_structure": "Face-centered cubic",
        },
        "applications": ["Catalysts", "Computer Hardware", "Medical (dental alloys)"],
        "producing_countries": {"Russia": 0.40, "South Africa": 0.36, "Other": 0.24},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Nb",
        "name": "Niobium",
        "category": "Refractory Metal",
        "physical_properties": {
            "color": "Grayish-blue when oxidized",
            "density_g_cm3": 8.57,
            "melting_point_c": 2477,
            "hardness_mohs": 6.0,
        },
        "chemical_properties": {
            "formula": "Nb",
            "reactivity": "Forms protective oxide layer, corrosion-resistant",
            "crystal_structure": "Body-centered cubic",
        },
        "applications": ["Metal Alloys", "Aerospace", "Medical (implants)"],
        "producing_countries": {"Brazil": 0.90, "Canada": 0.06, "Other": 0.04},
        "criticality": "High",
        "substitutability": "Low",
    },
    {
        "symbol": "Ta",
        "name": "Tantalum",
        "category": "Refractory Metal",
        "physical_properties": {
            "color": "Blue-gray",
            "density_g_cm3": 16.69,
            "melting_point_c": 3017,
            "hardness_mohs": 6.5,
        },
        "chemical_properties": {
            "formula": "Ta",
            "reactivity": "Highly corrosion-resistant, inert to most acids",
            "crystal_structure": "Body-centered cubic",
        },
        "applications": ["Computer Hardware", "Medical (implants)", "Aerospace"],
        "producing_countries": {"DRC": 0.40, "Rwanda": 0.24, "Other": 0.36},
        "criticality": "High",
        "substitutability": "Low",
    },
    {
        "symbol": "W",
        "name": "Tungsten",
        "category": "Refractory Metal",
        "physical_properties": {
            "color": "Grayish-white",
            "density_g_cm3": 19.25,
            "melting_point_c": 3422,
            "hardness_mohs": 7.5,
        },
        "chemical_properties": {
            "formula": "W",
            "reactivity": "Highly resistant to corrosion",
            "crystal_structure": "Body-centered cubic",
        },
        "applications": ["Metal Alloys", "Aerospace", "Catalysts"],
        "producing_countries": {"China": 0.82, "Vietnam": 0.05, "Other": 0.13},
        "criticality": "High",
        "substitutability": "Low",
    },
    {
        "symbol": "Ti",
        "name": "Titanium",
        "category": "Refractory Metal",
        "physical_properties": {
            "color": "Silvery",
            "density_g_cm3": 4.51,
            "melting_point_c": 1668,
            "hardness_mohs": 6.0,
        },
        "chemical_properties": {
            "formula": "Ti",
            "reactivity": "Forms passive oxide layer, highly corrosion-resistant",
            "crystal_structure": "Hexagonal close-packed",
        },
        "applications": ["Aerospace", "Medical (implants)", "Metal Alloys"],
        "producing_countries": {"China": 0.34, "Japan": 0.13, "Other": 0.53},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Be",
        "name": "Beryllium",
        "category": "Specialty Metal",
        "physical_properties": {
            "color": "Steel-gray",
            "density_g_cm3": 1.85,
            "melting_point_c": 1287,
            "hardness_mohs": 5.5,
        },
        "chemical_properties": {
            "formula": "Be",
            "reactivity": "Forms protective oxide layer; toxic dust hazard",
            "crystal_structure": "Hexagonal close-packed",
        },
        "applications": ["Aerospace", "Metal Alloys", "Computer Hardware (RF)"],
        "producing_countries": {"USA": 0.88, "China": 0.08, "Other": 0.04},
        "criticality": "High",
        "substitutability": "Low",
    },
    {
        "symbol": "Sb",
        "name": "Antimony",
        "category": "Specialty Metal",
        "physical_properties": {
            "color": "Silvery-white",
            "density_g_cm3": 6.68,
            "melting_point_c": 630.6,
            "hardness_mohs": 3.0,
        },
        "chemical_properties": {
            "formula": "Sb",
            "reactivity": "Resists attack by acids at room temperature",
            "crystal_structure": "Rhombohedral",
        },
        "applications": ["Metal Alloys", "Catalysts", "Aerospace (flame retardants)"],
        "producing_countries": {"China": 0.48, "Russia": 0.18, "Tajikistan": 0.15, "Other": 0.19},
        "criticality": "High",
        "substitutability": "Moderate",
    },
    {
        "symbol": "Re",
        "name": "Rhenium",
        "category": "Refractory Metal",
        "physical_properties": {
            "color": "Silvery-gray",
            "density_g_cm3": 21.02,
            "melting_point_c": 3186,
            "hardness_mohs": 7.0,
        },
        "chemical_properties": {
            "formula": "Re",
            "reactivity": "Highly resistant to corrosion, byproduct of Mo/Cu mining",
            "crystal_structure": "Hexagonal close-packed",
        },
        "applications": ["Aerospace (superalloys)", "Catalysts", "Metal Alloys"],
        "producing_countries": {"Chile": 0.52, "USA": 0.07, "Other": 0.41},
        "criticality": "High",
        "substitutability": "Very Low",
    },
    {
        "symbol": "Hf",
        "name": "Hafnium",
        "category": "Refractory Metal",
        "physical_properties": {
            "color": "Silvery-gray",
            "density_g_cm3": 13.31,
            "melting_point_c": 2233,
            "hardness_mohs": 5.5,
        },
        "chemical_properties": {
            "formula": "Hf",
            "reactivity": "Highly corrosion-resistant, low neutron absorption",
            "crystal_structure": "Hexagonal close-packed",
        },
        "applications": ["Aerospace", "Computer Hardware (semiconductors)", "Metal Alloys"],
        "producing_countries": {"France": 0.35, "China": 0.20, "Other": 0.45},
        "criticality": "High",
        "substitutability": "Low",
    },
]


def get_categories():
    return sorted(set(m["category"] for m in MINERALS))


def get_mineral_by_symbol(symbol):
    return next((m for m in MINERALS if m["symbol"] == symbol), None)