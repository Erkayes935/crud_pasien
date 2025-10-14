#!/usr/bin/env python3
"""
SCRIPT MANUAL APPROVAL RULES - AI META Backend
==============================================

Script sederhana untuk approve/reject rules secara manual dari backend
tanpa perlu dashboard UI.

Usage:
    python approve_rule.py --id 32 --action approve
    python approve_rule.py --id 33 --action reject --notes "Tidak sesuai PNPK"
    python approve_rule.py --list-pending  # Lihat rules menunggu approval
"""

import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Database connection config (sama dengan yang di core_engine)
DB_CONFIG = {
    'host': '27.112.78.243',
    'port': 5434,
    'database': 'patients',
    'user': 'postgres',
    'password': 'user'
}

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def list_pending_rules():
    """List all rules with status 'unverified'"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT id, diagnosis, field, layer, isi, sumber, rs_id, created_at
            FROM rules_master 
            WHERE status = 'unverified'
            ORDER BY created_at DESC
        """)
        
        rules = cursor.fetchall()
        
        if not rules:
            print("✅ Tidak ada rules yang menunggu approval")
            return
            
        print(f"\n📋 RULES MENUNGGU APPROVAL ({len(rules)} rules):")
        print("=" * 80)
        
        for rule in rules:
            print(f"ID: {rule['id']}")
            print(f"RS: {rule['rs_id']}")
            print(f"Layer: {rule['layer']}")
            print(f"Diagnosis: {rule['diagnosis']}")
            print(f"Field: {rule['field']}")
            print(f"Isi: {rule['isi'][:100]}{'...' if len(rule['isi']) > 100 else ''}")
            print(f"Sumber: {rule['sumber']}")
            print(f"Created: {rule['created_at']}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Error listing rules: {e}")
    finally:
        cursor.close()
        conn.close()

def approve_rule(rule_id, action, notes=None):
    """Approve or reject a rule"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # First check if rule exists and is unverified
        cursor.execute("""
            SELECT id, diagnosis, field, layer, rs_id, status
            FROM rules_master 
            WHERE id = %s
        """, (rule_id,))
        
        rule = cursor.fetchone()
        
        if not rule:
            print(f"❌ Rule dengan ID {rule_id} tidak ditemukan")
            return False
            
        if rule['status'] != 'unverified':
            print(f"❌ Rule ID {rule_id} sudah memiliki status: {rule['status']}")
            return False
            
        # Determine new status
        if action == 'approve':
            new_status = 'official'
            success_msg = "✅ DISETUJUI"
        elif action == 'reject':
            new_status = 'rejected'
            success_msg = "❌ DITOLAK"
        else:
            print(f"❌ Action '{action}' tidak valid. Gunakan 'approve' atau 'reject'")
            return False
            
        # Update rule status
        cursor.execute("""
            UPDATE rules_master 
            SET status = %s,
                approved_by = %s,
                approved_date = %s,
                review_notes = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            new_status,
            'ai_meta_backend',
            datetime.now(),
            notes or f"Manual {action} via backend script",
            datetime.now(),
            rule_id
        ))
        
        conn.commit()
        
        print(f"\n{success_msg}")
        print(f"Rule ID: {rule['id']}")
        print(f"RS: {rule['rs_id']}")
        print(f"Diagnosis: {rule['diagnosis']}")
        print(f"Field: {rule['field']}")
        print(f"Status: {rule['status']} → {new_status}")
        if notes:
            print(f"Notes: {notes}")
        print(f"Timestamp: {datetime.now()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating rule: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(
        description='Manual approval script for AI-CLAIM rules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python approve_rule.py --list-pending
  python approve_rule.py --id 32 --action approve
  python approve_rule.py --id 33 --action reject --notes "Tidak sesuai PNPK"
        """
    )
    
    parser.add_argument('--list-pending', action='store_true',
                       help='List all rules waiting for approval')
    parser.add_argument('--id', type=int,
                       help='Rule ID to approve/reject')
    parser.add_argument('--action', choices=['approve', 'reject'],
                       help='Action to take: approve or reject')
    parser.add_argument('--notes', type=str,
                       help='Optional notes for the approval/rejection')
    
    args = parser.parse_args()
    
    print("🤖 AI-CLAIM Rules Manual Approval Script")
    print("=" * 50)
    
    if args.list_pending:
        list_pending_rules()
    elif args.id and args.action:
        success = approve_rule(args.id, args.action, args.notes)
        if success:
            print("\n✅ Operasi berhasil!")
        else:
            print("\n❌ Operasi gagal!")
            sys.exit(1)
    else:
        parser.print_help()
        print("\n❌ Error: Gunakan --list-pending atau --id + --action")
        sys.exit(1)

if __name__ == '__main__':
    main()