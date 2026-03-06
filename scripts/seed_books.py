"""Seed the database with 25-100 sample books. Run from project root: python scripts/seed_books.py"""
import json
import sys
from pathlib import Path

# Add project root so app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal, init_db
from app.models.book import Book

SAMPLE_BOOKS = [
    {"title": "The Great Gatsby", "authors": ["F. Scott Fitzgerald"], "published_year": 1925, "tags": ["fiction", "classic"], "description": "A story of decadence and the American Dream."},
    {"title": "To Kill a Mockingbird", "authors": ["Harper Lee"], "published_year": 1960, "tags": ["fiction", "classic"], "description": "Racial injustice in the American South."},
    {"title": "1984", "authors": ["George Orwell"], "published_year": 1949, "tags": ["fiction", "dystopian"], "description": "Totalitarianism and surveillance."},
    {"title": "Pride and Prejudice", "authors": ["Jane Austen"], "published_year": 1813, "tags": ["fiction", "romance"], "description": "Elizabeth Bennet and Mr. Darcy."},
    {"title": "The Catcher in the Rye", "authors": ["J.D. Salinger"], "published_year": 1951, "tags": ["fiction"], "description": "Teenage alienation and loss of innocence."},
    {"title": "Harry Potter and the Philosopher's Stone", "authors": ["J.K. Rowling"], "published_year": 1997, "tags": ["fiction", "fantasy"], "description": "A young wizard discovers his destiny."},
    {"title": "The Hobbit", "authors": ["J.R.R. Tolkien"], "published_year": 1937, "tags": ["fiction", "fantasy"], "description": "Bilbo Baggins and the quest for treasure."},
    {"title": "Fahrenheit 451", "authors": ["Ray Bradbury"], "published_year": 1953, "tags": ["fiction", "dystopian"], "description": "Censorship and the burning of books."},
    {"title": "Jane Eyre", "authors": ["Charlotte Brontë"], "published_year": 1847, "tags": ["fiction", "romance"], "description": "An orphan's journey to independence."},
    {"title": "Animal Farm", "authors": ["George Orwell"], "published_year": 1945, "tags": ["fiction", "allegory"], "description": "A satirical allegory of totalitarianism."},
    {"title": "The Lord of the Rings", "authors": ["J.R.R. Tolkien"], "published_year": 1954, "tags": ["fiction", "fantasy"], "description": "The One Ring and the quest to destroy it."},
    {"title": "Wuthering Heights", "authors": ["Emily Brontë"], "published_year": 1847, "tags": ["fiction", "romance"], "description": "Passion and revenge on the Yorkshire moors."},
    {"title": "Brave New World", "authors": ["Aldous Huxley"], "published_year": 1932, "tags": ["fiction", "dystopian"], "description": "A futuristic society of genetic engineering."},
    {"title": "The Chronicles of Narnia", "authors": ["C.S. Lewis"], "published_year": 1950, "tags": ["fiction", "fantasy"], "description": "Adventures in a magical land."},
    {"title": "Moby-Dick", "authors": ["Herman Melville"], "published_year": 1851, "tags": ["fiction", "adventure"], "description": "Captain Ahab's obsession with the white whale."},
    {"title": "The Odyssey", "authors": ["Homer"], "published_year": 800, "tags": ["fiction", "epic"], "description": "Odysseus' long journey home."},
    {"title": "Crime and Punishment", "authors": ["Fyodor Dostoevsky"], "published_year": 1866, "tags": ["fiction", "psychological"], "description": "A man's guilt after murder."},
    {"title": "One Hundred Years of Solitude", "authors": ["Gabriel García Márquez"], "published_year": 1967, "tags": ["fiction", "magical realism"], "description": "The Buendía family over generations."},
    {"title": "The Alchemist", "authors": ["Paulo Coelho"], "published_year": 1988, "tags": ["fiction", "philosophy"], "description": "A shepherd's journey to find treasure."},
    {"title": "The Da Vinci Code", "authors": ["Dan Brown"], "published_year": 2003, "tags": ["fiction", "thriller"], "description": "A mystery involving secret societies."},
    {"title": "Dune", "authors": ["Frank Herbert"], "published_year": 1965, "tags": ["fiction", "sci-fi"], "description": "Desert planet and political intrigue."},
    {"title": "The Hitchhiker's Guide to the Galaxy", "authors": ["Douglas Adams"], "published_year": 1979, "tags": ["fiction", "sci-fi", "comedy"], "description": "The answer is 42."},
    {"title": "Slaughterhouse-Five", "authors": ["Kurt Vonnegut"], "published_year": 1969, "tags": ["fiction", "sci-fi"], "description": "Unstuck in time."},
    {"title": "The Kite Runner", "authors": ["Khaled Hosseini"], "published_year": 2003, "tags": ["fiction"], "description": "Friendship and redemption in Afghanistan."},
    {"title": "Life of Pi", "authors": ["Yann Martel"], "published_year": 2001, "tags": ["fiction"], "description": "A boy and a tiger on a lifeboat."},
    {"title": "The Book Thief", "authors": ["Markus Zusak"], "published_year": 2005, "tags": ["fiction", "historical"], "description": "A girl who steals books in Nazi Germany."},
    {"title": "The Handmaid's Tale", "authors": ["Margaret Atwood"], "published_year": 1985, "tags": ["fiction", "dystopian"], "description": "A theocratic regime and reproductive control."},
    {"title": "Beloved", "authors": ["Toni Morrison"], "published_year": 1987, "tags": ["fiction"], "description": "The legacy of slavery."},
    {"title": "The Road", "authors": ["Cormac McCarthy"], "published_year": 2006, "tags": ["fiction", "post-apocalyptic"], "description": "A father and son in a ruined world."},
    {"title": "Where the Crawdads Sing", "authors": ["Delia Owens"], "published_year": 2018, "tags": ["fiction"], "description": "A marsh girl and a murder mystery."},
    {"title": "Educated", "authors": ["Tara Westover"], "published_year": 2018, "tags": ["non-fiction", "memoir"], "description": "A memoir of self-education."},
    {"title": "Sapiens", "authors": ["Yuval Noah Harari"], "published_year": 2011, "tags": ["non-fiction", "history"], "description": "A brief history of humankind."},
    {"title": "Thinking, Fast and Slow", "authors": ["Daniel Kahneman"], "published_year": 2011, "tags": ["non-fiction", "psychology"], "description": "Two systems of thought."},
    {"title": "The Lean Startup", "authors": ["Eric Ries"], "published_year": 2011, "tags": ["non-fiction", "business"], "description": "Build-Measure-Learn for startups."},
    {"title": "Clean Code", "authors": ["Robert C. Martin"], "published_year": 2008, "tags": ["non-fiction", "programming"], "description": "A handbook of agile software craftsmanship."},
    {"title": "Designing Data-Intensive Applications", "authors": ["Martin Kleppmann"], "published_year": 2017, "tags": ["non-fiction", "programming"], "description": "Data systems and reliability."},
    {"title": "The Pragmatic Programmer", "authors": ["David Thomas", "Andrew Hunt"], "published_year": 1999, "tags": ["non-fiction", "programming"], "description": "Tips for software developers."},
    {"title": "Introduction to Algorithms", "authors": ["Thomas H. Cormen", "Charles E. Leiserson", "Ronald L. Rivest", "Clifford Stein"], "published_year": 1990, "tags": ["non-fiction", "programming"], "description": "The CLRS algorithms textbook."},
    {"title": "The Mythical Man-Month", "authors": ["Fred Brooks"], "published_year": 1975, "tags": ["non-fiction", "programming"], "description": "Essays on software engineering."},
    {"title": "Refactoring", "authors": ["Martin Fowler"], "published_year": 1999, "tags": ["non-fiction", "programming"], "description": "Improving the design of existing code."},
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Book).count()
        if existing > 0:
            print(f"Database already has {existing} books. Skipping seed (delete data to re-seed).")
            return
        for i, data in enumerate(SAMPLE_BOOKS):
            book = Book(
                title=data["title"],
                authors=json.dumps(data["authors"]),
                published_year=data.get("published_year"),
                tags=json.dumps(data.get("tags", [])),
                description=data.get("description"),
            )
            db.add(book)
        db.commit()
        count = len(SAMPLE_BOOKS)
        print(f"Seeded {count} books.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
