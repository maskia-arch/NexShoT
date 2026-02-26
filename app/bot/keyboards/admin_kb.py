from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_dashboard_kb(tier: str) -> InlineKeyboardMarkup:
    """
    Das Hauptmenü für den Admin. Passt sich dem Abo-Status an.
    """
    builder = InlineKeyboardBuilder()

    # Zeile 1: Kerngeschäft
    builder.button(text="📦 Produkte", callback_data="admin_products")
    builder.button(text="🛒 Bestellungen", callback_data="admin_orders")

    # Zeile 2: Einstellungen & Finanzen
    builder.button(text="💳 Zahlungen", callback_data="admin_settings")
    builder.button(text="⚙️ Shop Config", callback_data="shop_config")

    # Zeile 3: Marketing & Team (Tier abhängig)
    if tier in ['pro', 'master']:
        builder.button(text="📢 Broadcast", callback_data="admin_broadcast")
    else:
        builder.button(text="🔒 Broadcast (Pro)", callback_data="tier_locked_broadcast")

    if tier == 'master':
        builder.button(text="👥 Team (Master)", callback_data="admin_team")
    else:
        builder.button(text="🔒 Team (Master)", callback_data="tier_locked_team")

    # Zeile 4: Upselling & Support
    # Wenn nicht Master, zeige Upgrade Button
    if tier != 'master':
        builder.button(text=f"💎 Upgrade ({tier.upper()})", callback_data="admin_upgrade")
    
    builder.button(text="🆘 Support", callback_data="admin_support")

    # Layout: 2 Spalten, Rest automatisch
    builder.adjust(2)
    
    return builder.as_markup()

def get_products_kb(products: list) -> InlineKeyboardMarkup:
    """
    Generiert eine Liste aller Produkte zum Bearbeiten.
    products: Liste von Dicts [{'id': '...', 'name': '...', 'price': 10.0}]
    """
    builder = InlineKeyboardBuilder()

    # Für jedes Produkt ein Button
    for product in products:
        button_text = f"{product['name']} ({product['price']}€)"
        # Wir nutzen die ID im Callback, um später zu wissen, was geklickt wurde
        builder.button(text=button_text, callback_data=f"edit_prod_{product['id']}")

    # Aktions-Buttons unten
    builder.button(text="➕ Produkt hinzufügen", callback_data="add_product")
    builder.button(text="🔙 Zurück", callback_data="admin_dashboard")

    # Layout: 1 Spalte pro Produkt
    builder.adjust(1)

    return builder.as_markup()

def get_product_edit_kb(product_id: str, is_active: bool) -> InlineKeyboardMarkup:
    """
    Menü, wenn man ein einzelnes Produkt angeklickt hat.
    """
    builder = InlineKeyboardBuilder()
    
    # Toggle Status (Aktiv/Inaktiv)
    status_text = "⏸ Deaktivieren" if is_active else "▶️ Aktivieren"
    status_callback = f"prod_toggle_{product_id}"
    
    builder.button(text="✏️ Preis ändern", callback_data=f"prod_edit_price_{product_id}")
    builder.button(text="🖼 Bild ändern", callback_data=f"prod_edit_img_{product_id}")
    builder.button(text=status_text, callback_data=status_callback)
    builder.button(text="🗑 LÖSCHEN", callback_data=f"prod_delete_{product_id}")
    
    builder.button(text="🔙 Zurück zur Liste", callback_data="admin_products")
    
    builder.adjust(2, 2, 1) # 2 Buttons, 2 Buttons, 1 Button
    return builder.as_markup()

def get_payment_settings_kb(active_methods: list) -> InlineKeyboardMarkup:
    """
    Auswahl der Zahlungsmethoden.
    """
    builder = InlineKeyboardBuilder()

    # Neue Methode hinzufügen
    builder.button(text="➕ Bitcoin (BTC)", callback_data="add_pay_btc")
    builder.button(text="➕ PayPal", callback_data="add_pay_paypal")
    builder.button(text="➕ Ethereum (ETH)", callback_data="add_pay_eth")
    
    # Vorhandene Methoden verwalten (Optional, hier vereinfacht)
    # builder.button(text="Manage Active Methods", callback_data="manage_payments")

    builder.button(text="🔙 Zurück", callback_data="admin_dashboard")
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_cancel_kb() -> InlineKeyboardMarkup:
    """
    Ein einfacher 'Abbrechen' Button für State-Prozesse (z.B. beim Eingeben von Text).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Abbrechen", callback_data="admin_dashboard")
    return builder.as_markup()
