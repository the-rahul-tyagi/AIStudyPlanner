import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from planner.models import Subject, Topic

def seed_all():
    user = User.objects.first()
    if not user:
        print("No user found! Please register an account at /register/ first, then run this script again.")
        return

    print(f"Seeding data for user: {user.username}\n")

    data = [
        {
            "name": "Data Structures & Algorithms",
            "description": "Focuses on efficient data organization, storage mechanisms, and algorithmic problem-solving techniques such as searching, sorting, graph traversal, and dynamic programming.",
            "color": "#6366f1",
            "topics": ["Arrays & Strings", "Linked Lists", "Stacks & Queues", "Trees & Graphs", "Dynamic Programming"]
        },
        {
            "name": "Operating Systems",
            "description": "Covers core system management concepts including process scheduling, memory allocation, deadlocks, file systems, and virtual memory.",
            "color": "#06b6d4",
            "topics": ["Process Management", "CPU Scheduling", "Memory Management", "Virtual Memory", "File Systems"]
        },
        {
            "name": "Database Management Systems",
            "description": "Explores relational database design, ER modeling, SQL querying, normalization, indexing, and ACID transaction properties.",
            "color": "#10b981",
            "topics": ["ER Modeling", "Relational Algebra", "SQL Queries", "Normalization", "Transactions & Concurrency"]
        },
        {
            "name": "Web Development in Python",
            "description": "Focuses on building robust, scalable web applications and API integrations utilizing modern backend frameworks like Django and Python.",
            "color": "#a855f7",
            "topics": ["Django Architecture", "MVT Pattern", "ORM & Migrations", "Forms & Authentication", "REST APIs"]
        },
        {
            "name": "Artificial Intelligence & ML",
            "description": "Covers intelligent problem-solving agents, neural networks, supervised and unsupervised learning paradigms, and generative AI integrations.",
            "color": "#f59e0b",
            "topics": ["Search Algorithms", "Supervised Learning", "Neural Networks", "Unsupervised Learning", "NLP Basics"]
        },
        {
            "name": "Computer Networks",
            "description": "Studies network layering models (OSI/TCP-IP), routing protocols, transport layer reliability (TCP/UDP), and foundational web communication protocols.",
            "color": "#3b82f6",
            "topics": ["OSI & TCP/IP Models", "Routing Protocols", "TCP/UDP Protocols", "HTTP/HTTPS", "Network Security"]
        },
        {
            "name": "Software Engineering",
            "description": "Examines structured software development life cycles (SDLC), requirements specification (SRS), version control workflows, and automated testing strategies.",
            "color": "#ec4899",
            "topics": ["SDLC Models", "Requirements Engineering", "Agile & Scrum", "Version Control (Git)", "Software Testing"]
        },
        {
            "name": "Object-Oriented Programming",
            "description": "Teaches foundational software design principles including classes, objects, encapsulation, inheritance, and polymorphism.",
            "color": "#14b8a6",
            "topics": ["Classes & Objects", "Inheritance & Polymorphism", "Encapsulation", "Exception Handling", "Design Patterns"]
        },
        {
            "name": "Computer Architecture",
            "description": "Explores internal hardware-software interfaces, instruction set architectures (ISA), memory hierarchies, and CPU pipelining.",
            "color": "#8b5cf6",
            "topics": ["Instruction Set Architecture", "CPU Datapath", "Memory Hierarchy", "Pipelining", "Cache Memory"]
        },
        {
            "name": "Information Security",
            "description": "Covers core security principles, encryption standards, cryptographic hashing, and secure token-based authentication workflows.",
            "color": "#ef4444",
            "topics": ["CIA Triad", "Cryptography & Hashing", "Authentication & Authorization", "Web Security (OWASP Top 10)", "Network Firewalls"]
        },
    ]

    for item in data:
        subject, created = Subject.objects.get_or_create(
            user=user,
            name=item["name"],
            defaults={
                "description": item["description"],
                "color": item["color"]
            }
        )
        if not created:
            subject.description = item["description"]
            subject.color = item["color"]
            subject.save()
            print(f"Updated Subject: {subject.name}")
        else:
            print(f"Added Subject: {subject.name}")

        for topic_title in item["topics"]:
            _, t_created = Topic.objects.get_or_create(
                subject=subject,
                title=topic_title,
                defaults={"difficulty": "Medium"}
            )
            if t_created:
                print(f"   + Added Topic: {topic_title}")

    print("\nDone! All 10 subjects and 50 topics are ready.")

if __name__ == '__main__':
    seed_all()