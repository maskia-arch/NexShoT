-- 1. Shops Tabelle (Das Herzstück)
CREATE TABLE IF NOT EXISTS shops (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    owner_telegram_id BIGINT NOT NULL,
    bot_token TEXT NOT NULL, -- Wird verschlüsselt gespeichert
    bot_username TEXT,
    tier TEXT DEFAULT 'demo', -- 'demo', 'pro', 'ultra'
    status TEXT DEFAULT 'active', -- 'active', 'banned', 'expired'
    trial_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trial_end TIMESTAMP WITH TIME ZONE,
    subscription_end TIMESTAMP WITH TIME ZONE,
    config JSONB DEFAULT '{"welcome_text": "Willkommen!", "currency": "EUR"}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Produkte Tabelle
CREATE TABLE IF NOT EXISTS products (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id UUID REFERENCES shops(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    file_id TEXT, -- Telegram File ID für Bilder
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Digitale Schlüssel / Lagerbestand (Neu für automatischen Versand)
CREATE TABLE IF NOT EXISTS product_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id UUID REFERENCES shops(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- Der Key, Link oder Account-Daten
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Bestellungen (Orders)
CREATE TABLE IF NOT EXISTS orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id UUID REFERENCES shops(id) ON DELETE CASCADE,
    customer_telegram_id BIGINT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'paid', 'cancelled'
    payment_method TEXT, -- 'BTC', 'LTC', 'Manual', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Bestellte Positionen (Order Items) - Wichtig für Historie und Versand
CREATE TABLE IF NOT EXISTS order_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    product_name TEXT, -- Falls Produkt gelöscht wird, bleibt Name erhalten
    price_at_purchase DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Shop Zahlungsmethoden (Konfiguration durch Shop-Admin)
CREATE TABLE IF NOT EXISTS payment_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id UUID REFERENCES shops(id) ON DELETE CASCADE,
    method TEXT NOT NULL, -- z.B. 'BTC', 'LTC', 'SOL'
    wallet_address TEXT NOT NULL,
    instructions TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(shop_id, method) -- Verhindert doppelte Einträge pro Währung
);

-- 7. Team / Shop Admins (Für Mitarbeiter Zugriff)
CREATE TABLE IF NOT EXISTS shop_admins (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    shop_id UUID REFERENCES shops(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    role TEXT DEFAULT 'moderator',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(shop_id, telegram_user_id)
);

-- 8. Platform Config (Für DICH als Super-Admin)
CREATE TABLE IF NOT EXISTS platform_config (
    id SERIAL PRIMARY KEY,
    pro_label TEXT DEFAULT 'Pro Upgrade',
    ultra_label TEXT DEFAULT 'Ultra Unlimited',
    pro_price_ltc DECIMAL(10, 4) DEFAULT 0.5,
    ultra_price_ltc DECIMAL(10, 4) DEFAULT 1.5,
    wallet_btc TEXT,
    wallet_ltc TEXT,
    wallet_eth TEXT,
    wallet_sol TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Initiale Konfiguration anlegen (damit ID 1 existiert)
INSERT INTO platform_config (id, pro_label) VALUES (1, 'Pro Upgrade') 
ON CONFLICT (id) DO NOTHING;

-- INDEXE für Performance (Beschleunigt Abfragen drastisch)
CREATE INDEX IF NOT EXISTS idx_shops_owner ON shops(owner_telegram_id);
CREATE INDEX IF NOT EXISTS idx_products_shop ON products(shop_id);
CREATE INDEX IF NOT EXISTS idx_keys_product_used ON product_keys(product_id, is_used);
CREATE INDEX IF NOT EXISTS idx_orders_shop ON orders(shop_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_telegram_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
