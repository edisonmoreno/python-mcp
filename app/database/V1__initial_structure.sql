-- =====================================================
-- EXTENSIONES
-- =====================================================
CREATE EXTENSION IF NOT EXISTS vector;
-- habilita gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- =====================================================
-- FUNCIÓN PARA updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- =====================================================
-- TENANTS (empresas registradas)
-- =====================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'inactive')),
    plan VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenants_code UNIQUE (code)
);
CREATE TRIGGER trg_tenants_updated BEFORE
UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- =====================================================
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    -- 'whatsapp', 'telegram', 'web'
    type VARCHAR(30) NOT NULL DEFAULT 'whatsapp' CHECK (type IN ('whatsapp', 'telegram', 'web')),
    external_channel_id VARCHAR(50) NOT NULL,
    display_name VARCHAR(50),
    -- datos específicos del canal
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_channels_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_channels_type_external_channel_id UNIQUE (type, external_channel_id)
);
CREATE TRIGGER trg_channels_updated BEFORE
UPDATE ON channels FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- =====================================================
CREATE TABLE tenant_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id),
    agent_name VARCHAR(100) DEFAULT 'Asistente',
    system_prompt TEXT NOT NULL DEFAULT 'Eres un asistente útil.',
    chat JSONB NOT NULL DEFAULT '{
        "provider": "openai",
        "model": "gemini-3.5-flash-lite",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key": "",
        "temperature": 0.7,
        "timeout": 20,
        "max_retries": 5
    }',
    embedding JSONB NOT NULL DEFAULT '{
        "provider": "openai",
        "model": "text-embedding-3-small",
        "base_url": "https://otra.com",
        "api_key": "",
        "dimensions": 1536,
        "similarity_threshold": 0.70,
        "language": "es"
    }',
    business_hours JSONB DEFAULT '{}'::jsonb,
    extra_config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TRIGGER trg_tenant_settings_updated BEFORE
UPDATE ON tenant_settings FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'agent' CHECK (
        role IN ('owner', 'admin', 'agent')
    ),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    availability VARCHAR(20) NOT NULL DEFAULT 'offline' CHECK (
        availability IN ('online', 'busy', 'away', 'offline')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_tenant_id UNIQUE (tenant_id, id)
);
CREATE UNIQUE INDEX uq_users_tenant_email ON users (tenant_id, lower(email));
CREATE TRIGGER trg_users_updated BEFORE
UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- =====================================================
-- CONVERSATIONS (conversaciones por empresa y cliente)
-- =====================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    title VARCHAR(300) NOT NULL,
    type VARCHAR(30) NOT NULL DEFAULT 'document' CHECK (
        type IN (
            'document',
            'faq',
            'policy',
            'product',
            'url',
            'other'
        )
    ),
    source_type VARCHAR(30) DEFAULT 'upload' CHECK (
        source_type IN ('upload', 'url', 'manual', 'api')
    ),
    source_url TEXT,
    file_path TEXT,
    mime_type VARCHAR(100),
    -- SHA-256 para detectar cambios
    content_hash VARCHAR(64),
    ingestion_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        ingestion_status IN ('pending', 'processing', 'ready', 'failed')
    ),
    error_detail TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_documents_tenant_id UNIQUE (tenant_id, id)
);
CREATE UNIQUE INDEX uq_documents_tenant_content_hash ON documents (tenant_id, content_hash)
WHERE content_hash IS NOT NULL;
CREATE INDEX idx_documents_tenant_status ON documents(tenant_id, status);
CREATE TRIGGER trg_documents_updated BEFORE
UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- =====================================================
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    document_id UUID NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT,
    embedding_model VARCHAR(100),
    embedding vector(1536) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_document_chunks_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_document_chunks_tenant_chunk_index UNIQUE (tenant_id, document_id, chunk_index),
    CONSTRAINT fk_document_chunks_tenant_document FOREIGN KEY (tenant_id, document_id) REFERENCES documents(tenant_id, id)
);
-- Índice vectorial HNSW (similitud coseno)
CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
-- Búsqueda full-text (búsqueda híbrida)
ALTER TABLE document_chunks
ADD COLUMN content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('spanish', content)) STORED;
CREATE INDEX idx_chunks_tsv ON document_chunks USING gin(content_tsv);
-- =====================================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    channel_id UUID NOT NULL,
    customer_external_id VARCHAR(100) NOT NULL,
    customer_name VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (
        status IN ('open', 'closed', 'handoff', 'archived')
    ),
    assigned_user_id UUID,
    last_message_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_conversations_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_conversations_tenant_channel_id UNIQUE (tenant_id, channel_id, id),
    CONSTRAINT fk_conversations_tenant_channel FOREIGN KEY (tenant_id, channel_id) REFERENCES channels(tenant_id, id),
    CONSTRAINT fk_conversations_tenant_user FOREIGN KEY (tenant_id, assigned_user_id) REFERENCES users(tenant_id, id)
);
CREATE INDEX idx_conversations_tenant_customer ON conversations(tenant_id, customer_external_id);
CREATE INDEX idx_conversations_tenant_assigned_user_id ON conversations(tenant_id, assigned_user_id);
CREATE INDEX idx_conversations_tenant_last_message_at ON conversations(tenant_id, last_message_at DESC);
CREATE TRIGGER trg_conversations_updated BEFORE
UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- =====================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    channel_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer' CHECK (
        role IN ('customer', 'assistant', 'system', 'human_agent')
    ),
    message_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (
        message_type IN (
            'text',
            'image',
            'audio',
            'video',
            'document',
            'location',
            'template',
            'interactive'
        )
    ),
    content TEXT,
    media_url TEXT,
    external_message_id VARCHAR(200),
    status VARCHAR(20) DEFAULT 'received' CHECK (
        status IN (
            'received',
            'queued',
            'sent',
            'delivered',
            'read',
            'failed'
        )
    ),
    error_detail TEXT,
    model VARCHAR(100),
    -- prompt_tokens
    tokens_input INT,
    -- completion_tokens
    tokens_output INT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_messages_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_messages_tennat_channel_external_message_id UNIQUE (tenant_id, channel_id, external_message_id),
    CONSTRAINT fk_messages_tenant_channel FOREIGN KEY (tenant_id, channel_id) REFERENCES channels(tenant_id, id),
    CONSTRAINT fk_messages_tenant_channel_conversation FOREIGN KEY (tenant_id, channel_id, conversation_id) REFERENCES conversations (tenant_id, channel_id, id)
);
CREATE INDEX idx_messages_tenant_conversation_created ON messages(tenant_id, conversation_id, created_at DESC);
-- =====================================================
-- Fragmentos (chunks) de documentos que se usó para generar la respuesta
CREATE TABLE message_document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    message_id UUID NOT NULL,
    document_chunk_id UUID NOT NULL,
    -- posición en los resultados
    rank SMALLINT NOT NULL,
    -- similitud que obtuvo
    score REAL,
    CONSTRAINT uq_message_document_chunks_tenant_message_rank UNIQUE (tenant_id, message_id, rank),
    CONSTRAINT fk_message_document_chunks_tenant_message FOREIGN KEY (tenant_id, message_id) REFERENCES messages(tenant_id, id),
    CONSTRAINT fk_message_document_chunks_tenant_document_chunk FOREIGN KEY (tenant_id, document_chunk_id) REFERENCES document_chunks(tenant_id, id)
);
CREATE INDEX idx_message_document_chunks_tenant_document_chunk ON message_document_chunks(tenant_id, document_chunk_id);
-- =====================================================
-- FUNCIÓN ACTUALIZA FECHA ULTIMA CONVSERSACION
-- =====================================================
CREATE OR REPLACE FUNCTION touch_conversation() RETURNS TRIGGER AS $$ BEGIN
UPDATE conversations
SET last_message_at = GREATEST(last_message_at, NEW.created_at)
WHERE tenant_id = NEW.tenant_id
    AND id = NEW.conversation_id;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_messages_touch
AFTER
INSERT ON messages FOR EACH ROW EXECUTE FUNCTION touch_conversation();
-- =====================================================
-- FUNCIÓN DE BÚSQUEDA SEMÁNTICA POR TENANT
-- =====================================================
CREATE OR REPLACE FUNCTION match_chunks(
        p_tenant_id UUID,
        p_query_embedding vector(1536),
        p_match_count INT DEFAULT 5,
        p_min_similarity FLOAT DEFAULT 0.70
    ) RETURNS TABLE (
        id UUID,
        document_id UUID,
        document_title VARCHAR,
        content TEXT,
        similarity FLOAT
    ) LANGUAGE sql STABLE AS $$ WITH nearest AS (
        SELECT c.id,
            c.document_id,
            c.content,
            c.embedding <=> p_query_embedding AS distance
        FROM document_chunks c
        WHERE c.tenant_id = p_tenant_id
        ORDER BY c.embedding <=> p_query_embedding
        LIMIT p_match_count * 4 -- sobre-muestreo: luego se filtra por documento activo
    )
SELECT n.id,
    n.document_id,
    d.title,
    n.content,
    1 - n.distance
FROM nearest n
    JOIN documents d ON d.tenant_id = p_tenant_id
    AND d.id = n.document_id
WHERE d.ingestion_status = 'ready'
    AND d.status = 'active'
    AND 1 - n.distance >= p_min_similarity
ORDER BY n.distance
LIMIT p_match_count;
$$;