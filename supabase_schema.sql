-- =============================================
-- DASHBOARD VENDA DIRETA - SCHEMA SUPABASE
-- =============================================

-- 1. SETORES
create table if not exists setores (
    id serial primary key,
    nome text not null unique,
    tipo text not null check (tipo in ('base', 'financeiro')),
    ativo boolean not null default true,
    created_at timestamp default now()
);

-- 2. CICLOS
create table if not exists ciclos (
    id serial primary key,
    nome text not null unique,
    data_inicio date,
    data_fim date,
    ativo boolean not null default true,
    created_at timestamp default now()
);

-- 3. METAS POR SETOR/CICLO
create table if not exists metas (
    id serial primary key,
    ciclo_id integer references ciclos(id),
    setor_id integer references setores(id),
    -- Metas financeiras (R$)
    meta_boticario numeric default 0,
    meta_eudora numeric default 0,
    meta_oui numeric default 0,
    meta_qdb numeric default 0,
    meta_cabelos numeric default 0,
    meta_make numeric default 0,
    -- Metas percentuais
    meta_multimarcas numeric default 0,
    meta_pct_cabelos numeric default 0,
    meta_pct_make numeric default 0,
    meta_atividade numeric default 0,
    tamanho_base integer default 0,
    -- Metas base
    meta_inicios_reinicios integer default 0,
    realizado_inicios_reinicios integer default 0,
    -- Controle
    updated_at timestamp default now(),
    updated_by text,
    unique(ciclo_id, setor_id)
);

-- 4. CONFIGURAÇÕES DE PONTUAÇÃO
create table if not exists configuracoes (
    id serial primary key,
    chave text not null unique,
    valor text not null,
    descricao text,
    updated_at timestamp default now(),
    updated_by text
);

-- 5. RESULTADOS CALCULADOS POR CICLO/SETOR
create table if not exists resultados (
    id serial primary key,
    ciclo_id integer references ciclos(id),
    setor_id integer references setores(id),
    tipo text not null check (tipo in ('base', 'financeiro')),
    -- Resultados financeiros
    valor_boticario numeric default 0,
    valor_eudora numeric default 0,
    valor_oui numeric default 0,
    valor_qdb numeric default 0,
    valor_cabelos numeric default 0,
    valor_make numeric default 0,
    -- Resultados percentuais
    pct_multimarcas numeric default 0,
    pct_cabelos numeric default 0,
    pct_make numeric default 0,
    pct_atividade numeric default 0,
    ativos integer default 0,
    -- Resultados base
    inicios_reinicios integer default 0,
    -- IAF calculado
    pontuacao_obtida numeric default 0,
    pontuacao_maxima numeric default 0,
    iaf numeric default 0,
    classificacao text default 'Não Classificado',
    created_at timestamp default now(),
    unique(ciclo_id, setor_id)
);

-- 6. RESULTADOS ER (CAIXAS)
create table if not exists resultados_er (
    id serial primary key,
    ciclo_id integer references ciclos(id),
    usuario_finalizacao text not null,
    total_pedidos integer default 0,
    pedidos_nao_multimarca integer default 0,
    pct_nao_multimarca numeric default 0,
    created_at timestamp default now(),
    unique(ciclo_id, usuario_finalizacao)
);

-- 7. LOG DE UPLOADS
create table if not exists log_uploads (
    id serial primary key,
    ciclo_id integer references ciclos(id),
    arquivo text not null,
    usuario text not null,
    data_upload timestamp default now()
);

-- 8. LOG DE ALTERAÇÕES
create table if not exists log_alteracoes (
    id serial primary key,
    tabela text not null,
    campo text not null,
    valor_anterior text,
    valor_novo text,
    usuario text not null,
    created_at timestamp default now()
);

-- =============================================
-- CONFIGURAÇÕES PADRÃO
-- =============================================
insert into configuracoes (chave, valor, descricao) values
('pts_inicios_reinicios', '800', 'Pontuação máxima Inícios+Reinícios'),
('pts_meta_grupo', '200', 'Pontuação máxima Meta do Grupo'),
('faixa_bronze_min', '65', 'IAF mínimo Bronze (%)'),
('faixa_prata_min', '75', 'IAF mínimo Prata (%)'),
('faixa_ouro_min', '85', 'IAF mínimo Ouro (%)'),
('faixa_diamante_min', '95', 'IAF mínimo Diamante (%)'),
('faixa_pontuacao_50pct', '85', 'A partir de X% da meta = 50% dos pontos'),
('faixa_pontuacao_75pct', '95', 'A partir de X% da meta = 75% dos pontos'),
('faixa_pontuacao_100pct', '100', 'A partir de X% da meta = 100% dos pontos'),
('meta_nao_multimarca_caixa', '30', 'Meta máxima % não multimarca por caixa'),
('senha_leitura', 'leitura123', 'Senha perfil leitura'),
('senha_gerencia', 'gerencia123', 'Senha perfil gerência'),
('senha_admin', 'admin123', 'Senha perfil administrador')
on conflict (chave) do nothing;
