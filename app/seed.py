"""
Space Dungeon Sweatshop - Database Seeding
Populates the database with realistic data for all models.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine
from app.models import Agent, Base, Design, Product, ResearchFinding, Sale, Task

logger = logging.getLogger(__name__)

# ─── Seed Data Config ─────────────────────────────────────

AGENT_DATA = [
    {
        "name": "Ultron",
        "role": "overseer",
        "status": "working",
        "efficiency_pct": 97.5,
        "tasks_completed": 1847,
        "current_task": "Routing task #T-2841 to Forge",
    },
    {
        "name": "Forge",
        "role": "designer",
        "status": "working",
        "efficiency_pct": 92.3,
        "tasks_completed": 1243,
        "current_task": "Generating design for cosmic cat t-shirt",
    },
    {
        "name": "Nova",
        "role": "researcher",
        "status": "working",
        "efficiency_pct": 88.7,
        "tasks_completed": 956,
        "current_task": "Scraping Etsy competitor: StarDustPrints",
    },
    {
        "name": "Minion-1",
        "role": "worker",
        "status": "working",
        "efficiency_pct": 85.0,
        "tasks_completed": 3421,
        "current_task": "Syncing Etsy orders (batch #482)",
    },
    {
        "name": "Minion-2",
        "role": "worker",
        "status": "idle",
        "efficiency_pct": 91.2,
        "tasks_completed": 2890,
        "current_task": None,
    },
    {
        "name": "Minion-3",
        "role": "worker",
        "status": "idle",
        "efficiency_pct": 78.5,
        "tasks_completed": 1567,
        "current_task": None,
    },
]

TASK_TYPES = ["design", "research", "order", "other"]
TASK_STATUSES = ["pending", "running", "completed", "failed"]
TASK_PAYLOADS = {
    "design": [
        {"prompt": "Cosmic cat riding a rocket through nebula", "style": "vaporwave"},
        {"prompt": "Vintage astronaut holding a coffee mug on Mars", "style": "retro"},
        {"prompt": "Cyberpunk owl with neon circuit patterns", "style": "cyberpunk"},
        {"prompt": "Minimalist mountain landscape at golden hour", "style": "minimalist"},
        {"prompt": "Japanese koi fish swimming through space clouds", "style": "japanese"},
        {"prompt": "Steampunk mechanical butterfly with gears", "style": "steampunk"},
        {"prompt": "Psychedelic turtle with galaxy shell pattern", "style": "psychedelic"},
        {"prompt": "Abstract geometric wolf howling at moon", "style": "geometric"},
    ],
    "research": [
        {"store_url": "https://www.etsy.com/shop/StarDustPrints", "category": "space_tshirts"},
        {"store_url": "https://www.etsy.com/shop/MoonWaveDesigns", "category": "astronomy_posters"},
        {"store_url": "https://www.etsy.com/shop/NebulaArtCo", "category": "cosmic_mugs"},
        {"store_url": "https://www.etsy.com/shop/GalaxyGoodiesUS", "category": "scifi_apparel"},
    ],
    "order": [
        {"order_id": "ETSY-2025-001847", "action": "push_to_printify"},
        {"order_id": "ETSY-2025-001848", "action": "sync_inventory"},
        {"order_id": "SUP-2025-004291", "action": "fulfill_supplement"},
        {"order_id": "ETSY-2025-001849", "action": "update_listing"},
    ],
    "other": [
        {"action": "health_check", "target": "all_agents"},
        {"action": "generate_report", "type": "efficiency"},
        {"action": "cleanup_old_tasks", "retention_days": 30},
    ],
}

DESIGN_PROMPTS = [
    "Cosmic cat floating through a neon nebula with vaporwave aesthetic",
    "Vintage astronaut holding a steaming coffee cup on the surface of Mars",
    "Cyberpunk owl with glowing neon circuit board feather patterns",
    "Minimalist mountain range silhouette at golden hour with fog",
    "Japanese koi fish swimming through cosmic stardust clouds",
    "Steampunk mechanical butterfly with visible brass gears and steam",
    "Psychedelic sea turtle with a galaxy spiral pattern on its shell",
    "Abstract geometric wolf howling at a crescent moon made of triangles",
    "Retro 80s sun setting behind palm trees with synthwave grid",
    "Cute axolotl wearing a tiny astronaut helmet in zero gravity",
    "Mystical forest with bioluminescent mushrooms and fireflies",
    "Grumpy cactus wearing sunglasses in a desert sunset",
    "Space sloth hanging from a ringed planet with stars",
    "Floral skull made of roses and peonies with gold accents",
    "Dinosaurs in space suits exploring an alien planet",
]

PRODUCT_DATA = [
    # Etsy POD Store
    {"store": "etsy-pod", "title": "Cosmic Cat T-Shirt", "price": 28.99, "cost": 12.50, "type": "tshirt"},
    {"store": "etsy-pod", "title": "Astronaut Coffee Mug", "price": 19.99, "cost": 7.00, "type": "mug"},
    {"store": "etsy-pod", "title": "Cyber Owl Poster", "price": 24.99, "cost": 5.00, "type": "poster"},
    {"store": "etsy-pod", "title": "Mountain Fog T-Shirt", "price": 27.99, "cost": 12.50, "type": "tshirt"},
    {"store": "etsy-pod", "title": "Koi Nebula Hoodie", "price": 44.99, "cost": 18.00, "type": "tshirt"},
    {"store": "etsy-pod", "title": "Steampunk Butterfly Mug", "price": 18.99, "cost": 7.00, "type": "mug"},
    {"store": "etsy-pod", "title": "Galaxy Turtle Poster", "price": 22.99, "cost": 5.00, "type": "poster"},
    {"store": "etsy-pod", "title": "Geometric Wolf T-Shirt", "price": 26.99, "cost": 12.50, "type": "tshirt"},
    {"store": "etsy-pod", "title": "Synthwave Sunset Tee", "price": 29.99, "cost": 12.50, "type": "tshirt"},
    {"store": "etsy-pod", "title": "Space Axolotl Mug", "price": 21.99, "cost": 7.50, "type": "mug"},
    # Etsy Candles Store
    {"store": "etsy-candles", "title": "Nebula Dreams Soy Candle", "price": 34.99, "cost": 8.50, "type": "candle"},
    {"store": "etsy-candles", "title": "Moonlit Forest Candle", "price": 29.99, "cost": 7.00, "type": "candle"},
    {"store": "etsy-candles", "title": "Cosmic Vanilla Candle", "price": 32.99, "cost": 8.00, "type": "candle"},
    {"store": "etsy-candles", "title": "Stardust Lavender Candle", "price": 31.99, "cost": 7.50, "type": "candle"},
    {"store": "etsy-candles", "title": "Aurora Borealis Candle", "price": 36.99, "cost": 9.00, "type": "candle"},
    {"store": "etsy-candles", "title": "Galactic Rose Candle", "price": 33.99, "cost": 8.25, "type": "candle"},
    {"store": "etsy-candles", "title": "Supernova Citrus Candle", "price": 30.99, "cost": 7.75, "type": "candle"},
    {"store": "etsy-candles", "title": "Midnight Orchid Candle", "price": 35.99, "cost": 8.75, "type": "candle"},
    # Supplements Store
    {"store": "supplements", "title": "Cosmic Focus Nootropic", "price": 49.99, "cost": 12.00, "type": "supplement"},
    {"store": "supplements", "title": "Nebula Sleep Complex", "price": 39.99, "cost": 9.50, "type": "supplement"},
    {"store": "supplements", "title": "Stardust Energy Pre-Workout", "price": 44.99, "cost": 11.00, "type": "supplement"},
    {"store": "supplements", "title": "Galaxy Greens Superfood", "price": 54.99, "cost": 14.00, "type": "supplement"},
    {"store": "supplements", "title": "Meteor Multivitamin", "price": 34.99, "cost": 8.00, "type": "supplement"},
    {"store": "supplements", "title": "Lunar Collagen Peptides", "price": 42.99, "cost": 10.50, "type": "supplement"},
    {"store": "supplements", "title": "Solar Omega-3 Complex", "price": 38.99, "cost": 9.00, "type": "supplement"},
    {"store": "supplements", "title": "Astro Adaptogen Blend", "price": 47.99, "cost": 11.50, "type": "supplement"},
]

RESEARCH_DATA = [
    {"competitor_store": "StarDustPrints", "product_category": "space_tshirts", "trend_score": 87.5, "estimated_sales": 1240, "concept": "Cosmic animal illustrations with vaporwave colors"},
    {"competitor_store": "MoonWaveDesigns", "product_category": "astronomy_posters", "trend_score": 72.3, "estimated_sales": 890, "concept": "Minimalist celestial body art prints"},
    {"competitor_store": "NebulaArtCo", "product_category": "cosmic_mugs", "trend_score": 91.0, "estimated_sales": 2100, "concept": "Colorful nebula swirl patterns on drinkware"},
    {"competitor_store": "GalaxyGoodiesUS", "product_category": "scifi_apparel", "trend_score": 68.4, "estimated_sales": 650, "concept": "Retro sci-fi movie poster style clothing"},
    {"competitor_store": "CosmicCraftShop", "product_category": "space_candles", "trend_score": 84.2, "estimated_sales": 1580, "concept": "Space-themed scented candles with glitter"},
    {"competitor_store": "AstroWearStudio", "product_category": "astronomy_hoodies", "trend_score": 79.1, "estimated_sales": 1120, "concept": "Glow-in-the-dark constellation patterns"},
    {"competitor_store": "PlanetPrintShop", "product_category": "planetary_mugs", "trend_score": 93.5, "estimated_sales": 2450, "concept": "Realistic planet surface texture mugs"},
    {"competitor_store": "StellarSupplements", "product_category": "wellness_gummies", "trend_score": 76.8, "estimated_sales": 980, "concept": "Space-themed supplement packaging"},
    {"competitor_store": "OrbitOrganics", "product_category": "organic_tees", "trend_score": 65.2, "estimated_sales": 430, "concept": "Eco-friendly space themed apparel"},
    {"competitor_store": "VortexVinylDecals", "product_category": "space_stickers", "trend_score": 88.9, "estimated_sales": 1870, "concept": "Holographic space vinyl stickers"},
]

# ─── Seeding Functions ────────────────────────────────────


def random_date(days_back: int = 30) -> datetime:
    """Generate a random datetime within the last N days."""
    now = datetime.now(timezone.utc)
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return now - delta


async def seed_agents(session: AsyncSession) -> list[Agent]:
    """Seed the agents table with initial data."""
    result = await session.execute(select(Agent))
    if result.scalars().first():
        logger.info("Agents already seeded, skipping...")
        return []

    agents: list[Agent] = []
    for data in AGENT_DATA:
        agent = Agent(
            name=data["name"],
            role=data["role"],
            status=data["status"],
            efficiency_pct=data["efficiency_pct"],
            tasks_completed=data["tasks_completed"],
            current_task=data["current_task"],
            created_at=random_date(90),
        )
        session.add(agent)
        agents.append(agent)

    await session.flush()
    logger.info(f"Seeded {len(agents)} agents")
    return agents


async def seed_tasks(session: AsyncSession) -> list[Task]:
    """Seed the tasks table with realistic task data."""
    result = await session.execute(select(Task))
    if result.scalars().first():
        logger.info("Tasks already seeded, skipping...")
        return []

    tasks: list[Task] = []
    agent_ids = ["Ultron", "Forge", "Nova", "Minion-1", "Minion-2", "Minion-3"]

    for i in range(20):
        task_type = random.choice(TASK_TYPES)
        status = random.choice(TASK_STATUSES)
        payload = random.choice(TASK_PAYLOADS[task_type])

        created = random_date(14)
        started = None
        completed = None

        if status in ("running", "completed", "failed"):
            started = created + timedelta(minutes=random.randint(1, 60))
        if status in ("completed", "failed"):
            completed = started + timedelta(minutes=random.randint(5, 120)) if started else None

        error = None
        if status == "failed":
            error = random.choice([
                "API rate limit exceeded",
                "Printify connection timeout",
                "Invalid image format returned",
                "Etsy authentication expired",
                "Network error during upload",
            ])

        result_data = None
        if status == "completed":
            result_data = {"output": f"task_result_{i}", "success": True}

        task = Task(
            agent_id=random.choice(agent_ids),
            type=task_type,
            status=status,
            payload=payload,
            result=result_data,
            priority=random.randint(1, 5),
            created_at=created,
            started_at=started,
            completed_at=completed,
            error=error,
        )
        session.add(task)
        tasks.append(task)

    await session.flush()
    logger.info(f"Seeded {len(tasks)} tasks")
    return tasks


async def seed_designs(session: AsyncSession) -> list[Design]:
    """Seed the designs table with AI-generated design data."""
    result = await session.execute(select(Design))
    if result.scalars().first():
        logger.info("Designs already seeded, skipping...")
        return []

    designs: list[Design] = []
    product_types = ["tshirt", "mug", "poster", "candle", "supplement"]
    statuses = ["draft", "approved", "uploaded"]

    for i, prompt in enumerate(DESIGN_PROMPTS):
        ptype = product_types[i % len(product_types)]
        status = random.choice(statuses)

        image_urls = [
            f"https://images.unsplash.com/photo-{1500000000000 + i}-design",
            f"https://cdn.printify.com/mockups/{ptype}/{i + 100}",
            None,
        ]

        design = Design(
            task_id=random.randint(1, 20) if random.random() > 0.3 else None,
            prompt=prompt,
            image_url=random.choice(image_urls) if status != "draft" else None,
            product_type=ptype,
            status=status,
            printify_product_id=f"PR-{1000 + i}" if status == "uploaded" else None,
            etsy_listing_id=f"ETSY-LST-{8000 + i}" if status == "uploaded" else None,
            created_at=random_date(30),
        )
        session.add(design)
        designs.append(design)

    await session.flush()
    logger.info(f"Seeded {len(designs)} designs")
    return designs


async def seed_products(session: AsyncSession) -> list[Product]:
    """Seed the products table with realistic product data."""
    result = await session.execute(select(Product))
    if result.scalars().first():
        logger.info("Products already seeded, skipping...")
        return []

    products: list[Product] = []

    for i, data in enumerate(PRODUCT_DATA):
        design_id = (i % 15) + 1 if random.random() > 0.2 else None
        status = random.choice(["draft", "active", "paused"])
        sales_count = random.randint(0, 250) if status == "active" else 0
        revenue = round(sales_count * data["price"] * random.uniform(0.7, 1.0), 2)

        product = Product(
            design_id=design_id,
            store=data["store"],
            title=data["title"],
            description=f"Premium quality {data['type']} featuring unique AI-generated artwork. Perfect for space enthusiasts and dreamers.",
            price=data["price"],
            cost=data["cost"],
            printify_product_id=f"PR-{2000 + i}" if data["store"] == "etsy-pod" else None,
            etsy_listing_id=f"ETSY-LST-{9000 + i}" if data["store"].startswith("etsy") and status == "active" else None,
            supplifull_sku=f"SUP-{3000 + i}" if data["store"] == "supplements" else None,
            status=status,
            sales_count=sales_count,
            revenue=revenue,
            created_at=random_date(60),
        )
        session.add(product)
        products.append(product)

    await session.flush()
    logger.info(f"Seeded {len(products)} products")
    return products


async def seed_sales(session: AsyncSession) -> list[Sale]:
    """Seed the sales table with realistic order data."""
    result = await session.execute(select(Sale))
    if result.scalars().first():
        logger.info("Sales already seeded, skipping...")
        return []

    sales: list[Sale] = []
    platforms = ["etsy", "supplifull"]

    # Get active products
    result = await session.execute(
        select(Product).where(Product.status == "active")
    )
    active_products = result.scalars().all()

    if not active_products:
        logger.warning("No active products found, skipping sales seed")
        return []

    for i in range(35):
        product = random.choice(active_products)
        platform = platforms[0] if product.store.startswith("etsy") else "supplifull"
        amount = round(random.uniform(15.0, 120.0), 2)
        fee_rate = 0.065 if platform == "etsy" else 0.08
        platform_fee = round(amount * fee_rate, 2)
        net = round(amount - platform_fee, 2)

        sale = Sale(
            product_id=product.id,
            platform=platform,
            amount=amount,
            platform_fee=platform_fee,
            net=net,
            order_date=random_date(45),
        )
        session.add(sale)
        sales.append(sale)

    await session.flush()
    logger.info(f"Seeded {len(sales)} sales")
    return sales


async def seed_research(session: AsyncSession) -> list[ResearchFinding]:
    """Seed the research_findings table with competitor data."""
    result = await session.execute(select(ResearchFinding))
    if result.scalars().first():
        logger.info("Research findings already seeded, skipping...")
        return []

    findings: list[ResearchFinding] = []

    for data in RESEARCH_DATA:
        sent = data["trend_score"] > 80 and random.random() > 0.3
        finding = ResearchFinding(
            competitor_store=data["competitor_store"],
            product_category=data["product_category"],
            trend_score=data["trend_score"],
            estimated_sales=data["estimated_sales"],
            concept_extracted=data["concept"],
            sent_to_forge=sent,
            forge_design_id=random.randint(1, 10) if sent else None,
            created_at=random_date(20),
        )
        session.add(finding)
        findings.append(finding)

    await session.flush()
    logger.info(f"Seeded {len(findings)} research findings")
    return findings


async def seed_all() -> None:
    """
    Main entry point for database seeding.
    Creates tables if they don't exist and seeds all tables.
    """
    logger.info("Starting database seeding...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        try:
            await seed_agents(session)
            await seed_tasks(session)
            await seed_designs(session)
            await seed_products(session)
            await seed_sales(session)
            await seed_research(session)

            await session.commit()
            logger.info("Database seeding completed successfully!")

        except Exception as e:
            await session.rollback()
            logger.error(f"Database seeding failed: {e}")
            raise
