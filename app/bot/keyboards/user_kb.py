from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_kb(is_shop_owner: bool = False) -> InlineKeyboardMarkup:
    """
    Das Hauptmenü für den Endkunden (Startseite).
    """
    builder = InlineKeyboardBuilder()

    # Zeile 1: Die wichtigsten Funktionen
    builder.button(text="🛍 Produkte", callback_data="catalog_list")
    builder.button(text="🛒 Warenkorb", callback_data="cart_show")

    # Zeile 2: Sekundäre Funktionen
    builder.button(text="📦 Meine Bestellungen", callback_data="my_orders")
    builder.button(text="🆘 Support / Hilfe", callback_data="support_ticket")

    # Zusatz für den Besitzer (Shortcut zum Admin Panel)
    if is_shop_owner:
        builder.button(text="🔧 Admin Panel öffnen", callback_data="admin_dashboard")

    # Layout: 2 Buttons pro Zeile, Admin-Button alleine unten
    builder.adjust(2, 2, 1)
    
    return builder.as_markup()

def get_catalog_kb(products: list, page: int = 0) -> InlineKeyboardMarkup:
    """
    Erstellt eine Liste aller Produkte.
    products: Liste von Dicts aus Supabase [{'id': '...', 'name': '...', 'price': 10.0}]
    """
    builder = InlineKeyboardBuilder()

    # Wenn keine Produkte da sind
    if not products:
        builder.button(text="🔙 Zurück", callback_data="shop_start")
        return builder.as_markup()

    # Für jedes Produkt einen Button erstellen
    for product in products:
        # Text: "T-Shirt - 19.99€"
        btn_text = f"{product['name']} • {product['price']}€"
        builder.button(text=btn_text, callback_data=f"prod_view_{product['id']}")

    # Navigation (Zurück zum Hauptmenü)
    builder.button(text="🔙 Hauptmenü", callback_data="shop_start")
    builder.button(text="🛒 Zum Warenkorb", callback_data="cart_show")

    # Layout: 1 Produkt pro Zeile, Navigation unten 2 nebeneinander
    builder.adjust(1, 2)

    return builder.as_markup()

def get_product_detail_kb(product_id: str, price: float) -> InlineKeyboardMarkup:
    """
    Ansicht eines einzelnen Produkts.
    """
    builder = InlineKeyboardBuilder()

    # Der wichtigste Button: Kaufen
    builder.button(text=f"🛒 In den Warenkorb ({price}€)", callback_data=f"cart_add_{product_id}")
    
    # Navigation
    builder.button(text="🔙 Zur Übersicht", callback_data="catalog_list")
    builder.button(text="🛒 Warenkorb ansehen", callback_data="cart_show")

    builder.adjust(1, 2)
    return builder.as_markup()

def get_cart_kb(total_price: float, is_empty: bool = False) -> InlineKeyboardMarkup:
    """
    Warenkorb-Aktionen.
    """
    builder = InlineKeyboardBuilder()

    if is_empty:
        builder.button(text="🛍 Jetzt einkaufen", callback_data="catalog_list")
        builder.button(text="🔙 Hauptmenü", callback_data="shop_start")
        builder.adjust(1)
    else:
        # Checkout Prozess starten
        builder.button(text=f"💳 Zur Kasse ({total_price:.2f}€)", callback_data="checkout_start")
        
        # Warenkorb leeren
        builder.button(text="🗑 Alles löschen", callback_data="cart_clear")
        
        # Weiter shoppen
        builder.button(text="🔙 Weiter shoppen", callback_data="catalog_list")
        
        builder.adjust(1, 2)

    return builder.as_markup()

def get_payment_methods_kb(methods: list) -> InlineKeyboardMarkup:
    """
    Zeigt alle verfügbaren Zahlungsmethoden im Checkout an.
    methods: Liste aus DB [{'id': '...', 'provider': 'paypal', ...}]
    """
    builder = InlineKeyboardBuilder()

    for method in methods:
        provider_name = method['provider'].upper() # z.B. PAYPAL
        # Wir nutzen die ID der Config, um später die Details zu laden
        builder.button(text=f"Bezahlen mit {provider_name}", callback_data=f"pay_select_{method['id']}")

    builder.button(text="❌ Abbrechen", callback_data="cart_show")
    
    # 1 Button pro Zeile
    builder.adjust(1)
    return builder.as_markup()

def get_payment_confirm_kb() -> InlineKeyboardMarkup:
    """
    Bestätigung nachdem der User die Adresse eingegeben hat.
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Ich habe bezahlt", callback_data="confirm_paid")
    builder.button(text="❌ Abbrechen", callback_data="shop_start")
    
    builder.adjust(1, 1)
    return builder.as_markup()

def get_cancel_kb() -> InlineKeyboardMarkup:
    """
    Universeller Abbrechen-Button für Eingabeprozesse (z.B. Adresse eingeben).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Abbrechen", callback_data="shop_start")
    return builder.as_markup()
