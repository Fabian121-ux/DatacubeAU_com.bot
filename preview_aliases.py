import asyncio
import argparse
from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from app.db import SessionLocal
from app.models.schema import Contact, ContactAlias, AdminAccount

async def preview_aliases():
    async with SessionLocal() as db:
        # 1. Verify Primary Admin
        print("=== Admin Accounts ===")
        admins = (await db.execute(select(AdminAccount))).scalars().all()
        for admin in admins:
            print(f"- {admin.name} ({admin.whatsapp_number}) | Role: {admin.role} | Primary: {admin.is_primary}")
        if not any(a.is_primary for a in admins):
            print("WARNING: No primary admin configured.")
            
        print("\n=== Phantom Aliases & Duplicate Contacts Preview ===")
        # Phantom aliases are Contacts whose whatsapp_id is just digits or otherwise doesn't match standard patterns,
        # but might correspond to the same person. Let's find contacts that share the same normalized_phone
        # or where a ContactAlias points to a Contact but another Contact exists with that raw_identifier.
        
        # Contacts with the same normalized_phone
        subq = (
            select(Contact.normalized_phone)
            .where(Contact.normalized_phone.isnot(None))
            .group_by(Contact.normalized_phone)
            .having(func.count(Contact.id) > 1)
            .subquery()
        )
        
        duplicates = (
            await db.execute(
                select(Contact).where(Contact.normalized_phone.in_(select(subq)))
                .order_by(Contact.normalized_phone)
            )
        ).scalars().all()
        
        if duplicates:
            print("Found potential duplicate contacts (sharing the same normalized_phone):")
            current_phone = None
            for contact in duplicates:
                if contact.normalized_phone != current_phone:
                    current_phone = contact.normalized_phone
                    print(f"\nPhone: {current_phone}")
                print(f"  - Contact ID: {contact.id} | whatsapp_id: {contact.whatsapp_id} | Name: {contact.display_name}")
        else:
            print("No duplicate contacts found sharing the same normalized_phone.")
            
        # Check ContactAlias mapping to existing Contacts
        stmt = (
            select(ContactAlias, Contact)
            .join(Contact, ContactAlias.contact_id == Contact.id)
        )
        aliases = (await db.execute(stmt)).all()
        
        if aliases:
            print("\nExisting Contact Aliases:")
            for alias, contact in aliases:
                print(f"  - Alias '{alias.raw_identifier}' -> Contact {contact.id} ({contact.whatsapp_id})")
        else:
            print("\nNo contact aliases configured.")
            
        print("\nNote: Run this script on the production environment to preview duplicate contacts and phantom aliases before performing any manual merges.")

if __name__ == "__main__":
    asyncio.run(preview_aliases())
