import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Venda Direta", page_icon="💼", layout="wide")

st.markdown("""<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="metric-container"] { background: white; border-radius:10px; padding:12px; border:1px solid #eee; }
</style>""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://bddjuowbotsybamawsts.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkZGp1b3dib3RzeWJhbWF3c3RzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzNzE3MjAsImV4cCI6MjA5MTk0NzcyMH0.QHDO0Ebfbx4rcV327g1KXD4Ep-jRstQXil_B6L445VU")

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_config(chave, default=None):
    try:
        res = get_supabase().table("configuracoes").select("valor").eq("chave", chave).single().execute()
        return res.data["valor"] if res.data else default
    except:
        return default

def set_config(chave, valor, usuario):
    sb = get_supabase()
    old = get_config(chave)
    sb.table("configuracoes").upsert({"chave": chave, "valor": str(valor), "updated_by": usuario}).execute()
    sb.table("log_alteracoes").insert({"tabela": "configuracoes", "campo": chave,
        "valor_anterior": str(old), "valor_novo": str(valor), "usuario": usuario}).execute()

def get_ciclos():
    res = get_supabase().table("ciclos").select("*").order("id", desc=True).execute()
    return res.data or []

def get_ciclo_ativo():
    res = get_supabase().table("ciclos").select("*").eq("ativo", True).order("id", desc=True).limit(1).execute()
    return res.data[0] if res.data else None

def get_setores(apenas_ativos=True, tipo=None):
    q = get_supabase().table("setores").select("*")
    if apenas_ativos: q = q.eq("ativo", True)
    if tipo: q = q.eq("tipo", tipo)
    return q.order("nome").execute().data or []

def get_metas(ciclo_id, setor_id=None):
    q = get_supabase().table("metas").select("*").eq("ciclo_id", ciclo_id)
    if setor_id: q = q.eq("setor_id", setor_id)
    return q.execute().data or []

def get_resultados(ciclo_id, tipo=None):
    q = get_supabase().table("resultados").select("*").eq("ciclo_id", ciclo_id)
    if tipo: q = q.eq("tipo", tipo)
    return q.execute().data or []

def get_resultados_er(ciclo_id):
    return get_supabase().table("resultados_er").select("*").eq("ciclo_id", ciclo_id).order("pct_nao_multimarca", desc=True).execute().data or []

def get_logs_upload(ciclo_id):
    return get_supabase().table("log_uploads").select("*").eq("ciclo_id", ciclo_id).order("data_upload", desc=True).execute().data or []

def log_upload(ciclo_id, arquivo, usuario):
    get_supabase().table("log_uploads").insert({"ciclo_id": ciclo_id, "arquivo": arquivo, "usuario": usuario}).execute()

def upsert_meta(ciclo_id, setor_id, dados):
    dados['ciclo_id'] = ciclo_id
    dados['setor_id'] = setor_id
    get_supabase().table("metas").upsert(dados, on_conflict="ciclo_id,setor_id").execute()

PERFIS = {"leitura": 1, "gerencia": 2, "admin": 3}

def check_auth():
    if "perfil" not in st.session_state: st.session_state.perfil = None
    if "usuario" not in st.session_state: st.session_state.usuario = None

def login_screen():
    st.markdown("## 🔐 Dashboard Venda Direta")
    st.markdown("---")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        nome = st.text_input("Seu nome")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True, type="primary"):
            if not nome:
                st.error("Informe seu nome.")
            elif senha == get_config("senha_admin", "admin123"):
                st.session_state.perfil = "admin"; st.session_state.usuario = nome; st.rerun()
            elif senha == get_config("senha_gerencia", "gerencia123"):
                st.session_state.perfil = "gerencia"; st.session_state.usuario = nome; st.rerun()
            elif senha == get_config("senha_leitura", "leitura123"):
                st.session_state.perfil = "leitura"; st.session_state.usuario = nome; st.rerun()
            else:
                st.error("Senha incorreta.")

def requer_perfil(p):
    if PERFIS.get(st.session_state.get("perfil"), 0) < PERFIS.get(p, 99):
        st.warning("⛔ Sem permissão."); st.stop()

def cor_class(c):
    return {'Diamante':'#1565C0','Ouro':'#F9A825','Prata':'#607D8B','Bronze':'#A1887F'}.get(c,'#9E9E9E')

def emoji_class(c):
    return {'Diamante':'💎','Ouro':'🥇','Prata':'🥈','Bronze':'🥉'}.get(c,'—')

def class_iaf(iaf, cfg):
    if iaf >= float(cfg.get('faixa_diamante_min',95)): return 'Diamante'
    if iaf >= float(cfg.get('faixa_ouro_min',85)): return 'Ouro'
    if iaf >= float(cfg.get('faixa_prata_min',75)): return 'Prata'
    if iaf >= float(cfg.get('faixa_bronze_min',65)): return 'Bronze'
    return 'Não Classificado'

def calc_pts(realizado, meta, pts_max, f50, f75, f100):
    if meta <= 0: return 0.0
    p = realizado / meta * 100
    if p >= f100: return pts_max
    if p >= f75: return pts_max * 0.75
    if p >= f50: return pts_max * 0.50
    return 0.0

def ler_planilha(arquivo, marca):
    df = pd.read_excel(arquivo)
    df['Marca'] = marca
    return df[~df['ValorPraticado'].isin([0,6])] if marca == 'Oui' else df[df['ValorPraticado'] > 0]

def calc_multimarcas(df_ativos, dfs):
    at = df_ativos[df_ativos['ValorPraticado'] > 0].copy()
    cods = set(at['CodigoRevendedora'].unique())
    cnt = {c: 0 for c in cods}
    for m in ['Boticario','Eudora','Oui','QDB']:
        if m in dfs:
            for c in cods:
                if c in set(dfs[m]['CodigoRevendedora'].unique()): cnt[c] += 1
    multi = {c for c,n in cnt.items() if n >= 2}
    at['is_multimarca'] = at['CodigoRevendedora'].isin(multi)
    return at

def processar_ciclo(dfs, metas_list, setores_list, cfg):
    df_ativos = dfs.get('Ativos')
    f50,f75,f100 = float(cfg.get('faixa_pontuacao_50pct',85)), float(cfg.get('faixa_pontuacao_75pct',95)), float(cfg.get('faixa_pontuacao_100pct',100))
    pts_ir = float(cfg.get('pts_inicios_reinicios',800))
    pts_g = float(cfg.get('pts_meta_grupo',200))
    pts_m = float(cfg.get('pts_por_marca_receita',100))
    pts_mu = float(cfg.get('pts_multimarcas',100))
    pts_cab = float(cfg.get('pts_pct_cabelos',100))
    pts_mak = float(cfg.get('pts_pct_make',100))
    pts_at = float(cfg.get('pts_atividade',100))
    md = {m['setor_id']:m for m in metas_list}
    df_multi = calc_multimarcas(df_ativos, dfs) if df_ativos is not None else None
    resultados = []
    for s in setores_list:
        sid,nome,tipo = s['id'],s['nome'],s['tipo']
        meta = md.get(sid,{})
        if tipo == 'base':
            real = int(meta.get('realizado_inicios_reinicios',0))
            m_ir = int(meta.get('meta_inicios_reinicios',0))
            pts = calc_pts(real, m_ir, pts_ir, f50, f75, f100)
            resultados.append({'setor_id':sid,'tipo':'base','valor_boticario':0,'valor_eudora':0,
                'valor_oui':0,'valor_qdb':0,'valor_cabelos':0,'valor_make':0,
                'pct_multimarcas':0,'pct_cabelos':0,'pct_make':0,'pct_atividade':0,
                'ativos':0,'inicios_reinicios':real,'pontuacao_obtida':pts,
                'pontuacao_maxima':pts_ir,'iaf':0.0,'classificacao':'Não Classificado'})
        else:
            vals,po,pm = {},0.0,0.0
            for marca,cv,cm in [('Boticario','valor_boticario','meta_boticario'),
                                  ('Eudora','valor_eudora','meta_eudora'),('Oui','valor_oui','meta_oui'),
                                  ('QDB','valor_qdb','meta_qdb'),('Cabelos','valor_cabelos','meta_cabelos'),
                                  ('Make','valor_make','meta_make')]:
                df = dfs.get(marca)
                val = df[df['Setor']==nome]['ValorPraticado'].sum() if df is not None else 0.0
                vals[cv] = val
                mv = float(meta.get(cm,0))
                if mv > 0: po += calc_pts(val,mv,pts_m,f50,f75,f100); pm += pts_m
            at_s = None; n_at = 0
            if df_ativos is not None:
                at_s = df_ativos[(df_ativos['Setor']==nome)&(df_ativos['ValorPraticado']>0)]
                n_at = at_s['CodigoRevendedora'].nunique()
            pct_mu = 0.0
            if df_multi is not None and n_at > 0:
                pct_mu = df_multi[(df_multi['Setor']==nome)&(df_multi['is_multimarca'])]['CodigoRevendedora'].nunique()/n_at*100
            m_mu = float(meta.get('meta_multimarcas',0))
            if m_mu > 0: po += calc_pts(pct_mu,m_mu,pts_mu,f50,f75,f100); pm += pts_mu
            pct_cab_v = 0.0
            if dfs.get('Cabelos') is not None and n_at > 0 and at_s is not None:
                cc = set(dfs['Cabelos'][dfs['Cabelos']['Setor']==nome]['CodigoRevendedora'].unique())
                ca = set(at_s['CodigoRevendedora'].unique())
                pct_cab_v = len(ca&cc)/n_at*100
            m_cab = float(meta.get('meta_pct_cabelos',0))
            if m_cab > 0: po += calc_pts(pct_cab_v,m_cab,pts_cab,f50,f75,f100); pm += pts_cab
            pct_mak_v = 0.0
            if dfs.get('Make') is not None and n_at > 0 and at_s is not None:
                cm2 = set(dfs['Make'][dfs['Make']['Setor']==nome]['CodigoRevendedora'].unique())
                ca2 = set(at_s['CodigoRevendedora'].unique())
                pct_mak_v = len(ca2&cm2)/n_at*100
            m_mak = float(meta.get('meta_pct_make',0))
            if m_mak > 0: po += calc_pts(pct_mak_v,m_mak,pts_mak,f50,f75,f100); pm += pts_mak
            tb = int(meta.get('tamanho_base',0))
            pct_at_v = n_at/tb*100 if tb > 0 else 0.0
            m_at = float(meta.get('meta_atividade',0))
            if m_at > 0: po += calc_pts(pct_at_v,m_at,pts_at,f50,f75,f100); pm += pts_at
            iaf = po/pm*100 if pm > 0 else 0.0
            resultados.append({'setor_id':sid,'tipo':'financeiro',**vals,
                'pct_multimarcas':round(pct_mu,2),'pct_cabelos':round(pct_cab_v,2),
                'pct_make':round(pct_mak_v,2),'pct_atividade':round(pct_at_v,2),
                'ativos':n_at,'inicios_reinicios':0,'pontuacao_obtida':round(po,2),
                'pontuacao_maxima':round(pm,2),'iaf':round(iaf,2),'classificacao':class_iaf(iaf,cfg)})
    base_res = [r for r in resultados if r['tipo']=='base']
    t_real = sum(r['inicios_reinicios'] for r in base_res)
    t_meta = sum(int(md.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in setores_list if s['tipo']=='base')
    gb = t_meta > 0 and t_real >= t_meta
    for r in base_res:
        r['pontuacao_obtida'] += pts_g if gb else 0
        r['pontuacao_maxima'] += pts_g
        r['iaf'] = round(r['pontuacao_obtida']/r['pontuacao_maxima']*100 if r['pontuacao_maxima']>0 else 0, 2)
        r['classificacao'] = class_iaf(r['iaf'],cfg)
    er_res = []
    if df_ativos is not None and dfs.get('ER') is not None and df_multi is not None:
        nao_m = set(df_multi[~df_multi['is_multimarca']]['CodigoRevendedora'].unique())
        df_er = dfs['ER'].copy()
        df_er['is_nm'] = df_er['Pessoa'].isin(nao_m)
        for u,g in df_er.groupby('Usuario de Finalização'):
            tot = len(g); nm = int(g['is_nm'].sum())
            er_res.append({'usuario_finalizacao':u,'total_pedidos':tot,'pedidos_nao_multimarca':nm,
                           'pct_nao_multimarca':round(nm/tot*100 if tot>0 else 0,2)})
        er_res.sort(key=lambda x: x['pct_nao_multimarca'], reverse=True)
    return {'resultados':resultados,'resultados_er':er_res,'t_real':t_real,'t_meta':t_meta}

def card_iaf(nome, iaf, cl, po, pm, delta=None):
    cor = cor_class(cl); em = emoji_class(cl)
    dh = f'<span style="color:{"#4CAF50" if (delta or 0)>=0 else "#F44336"};font-size:12px">{"▲" if (delta or 0)>=0 else "▼"} {abs(delta or 0):.1f}% vs ant.</span>' if delta is not None else ""
    st.markdown(f"""<div style="border:2px solid {cor};border-radius:12px;padding:16px;margin-bottom:12px;background:white">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:15px">{nome}</span>
            <span style="background:{cor};color:white;padding:4px 10px;border-radius:20px;font-size:12px">{em} {cl}</span>
        </div>
        <div style="margin-top:12px">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <span style="font-size:13px;color:#666">IAF</span>
                <span style="font-weight:600;font-size:20px;color:{cor}">{iaf:.1f}%</span>
            </div>
            <div style="background:#eee;border-radius:6px;height:10px;overflow:hidden">
                <div style="background:{cor};width:{min(iaf,100):.1f}%;height:100%;border-radius:6px"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:6px">
                <span style="font-size:12px;color:#999">{po:.0f}/{pm:.0f} pts</span>{dh}
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

def semaforo(realizado, meta, label, fmt="numero"):
    pct = realizado/meta*100 if meta>0 else 0
    cor = "#9E9E9E" if meta<=0 else ("#4CAF50" if pct>=100 else ("#FFC107" if pct>=95 else "#F44336"))
    ic = "⚪" if meta<=0 else ("🟢" if pct>=100 else ("🟡" if pct>=95 else "🔴"))
    vs = f"R$ {realizado:,.2f}" if fmt=="moeda" else (f"{realizado:.1f}%" if fmt=="pct" else str(int(realizado)))
    ms = f"R$ {meta:,.2f}" if fmt=="moeda" else (f"{meta:.1f}%" if fmt=="pct" else str(int(meta)))
    st.markdown(f"""<div style="background:#f9f9f9;border-left:4px solid {cor};border-radius:6px;padding:10px 14px;margin-bottom:8px">
        <div style="display:flex;justify-content:space-between"><span style="font-size:13px;color:#555">{ic} {label}</span>
        <span style="font-weight:600;font-size:14px;color:{cor}">{vs}</span></div>
        <div style="font-size:11px;color:#999;margin-top:2px">Meta: {ms} | {pct:.1f}%</div>
    </div>""", unsafe_allow_html=True)

def termometro(real, meta, label):
    pct = min(real/meta*100,100) if meta>0 else 0
    cor = "#4CAF50" if pct>=100 else ("#FFC107" if pct>=95 else "#F44336")
    st.markdown(f"""<div style="background:white;border-radius:12px;padding:16px;border:1px solid #eee;margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:10px">{label}</div>
        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:13px;color:#666">{real} realizados</span>
            <span style="font-size:13px;color:#666">Meta: {meta}</span>
        </div>
        <div style="background:#eee;border-radius:8px;height:16px;overflow:hidden">
            <div style="background:{cor};width:{pct:.1f}%;height:100%;border-radius:8px"></div>
        </div>
        <div style="text-align:center;margin-top:6px;font-weight:700;font-size:18px;color:{cor}">{pct:.1f}%</div>
    </div>""", unsafe_allow_html=True)

def badge_arq(nome, ok, data=None):
    cor = "#4CAF50" if ok else "#F44336"
    st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:8px;
        border:1px solid {cor}33;background:{cor}11;margin-bottom:6px">
        <span style="font-size:13px">{"✅" if ok else "❌"} <b>{nome}</b></span>
        <span style="font-size:11px;color:{cor}">{(data or "")[:16] if ok else "Aguardando"}</span>
    </div>""", unsafe_allow_html=True)

ARQS = ['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos','ER']
MARCAS_CFG = [('valor_boticario','meta_boticario','Boticário','💜'),
              ('valor_eudora','meta_eudora','Eudora','🟡'),
              ('valor_oui','meta_oui','OUI','🩷'),
              ('valor_qdb','meta_qdb','QDB','🟠'),
              ('valor_cabelos','meta_cabelos','Cabelos','🟤'),
              ('valor_make','meta_make','Make B.','🔵')]
INDS_PCT = [('pct_multimarcas','meta_multimarcas','Multimarcas'),
            ('pct_cabelos','meta_pct_cabelos','Cabelos %'),
            ('pct_make','meta_pct_make','Make %'),
            ('pct_atividade','meta_atividade','Atividade')]

def pg_home():
    ciclo = get_ciclo_ativo()
    if ciclo:
        st.markdown(f"## 🏠 Visão Geral — Ciclo **{ciclo['nome']}**")
    else:
        st.markdown("## 🏠 Visão Geral")
        st.warning("⚠️ Nenhum ciclo ativo. Configure em Configurações → Ciclos & Metas.")
        return
    st.markdown("---")
    logs = get_logs_upload(ciclo['id'])
    arqs_ok = {l['arquivo'] for l in logs}
    arqs_data = {l['arquivo']:l['data_upload'] for l in logs}
    st.markdown("### 📁 Status dos Arquivos")
    cols = st.columns(4)
    for i,a in enumerate(ARQS):
        with cols[i%4]: badge_arq(a, a in arqs_ok, arqs_data.get(a))
    falt = [a for a in ARQS if a not in arqs_ok]
    st.warning(f"⚠️ Pendentes: {', '.join(falt)}") if falt else st.success("✅ Todos os arquivos carregados!")
    st.markdown("---")
    res = get_resultados(ciclo['id'])
    if not res:
        st.info("📊 Aguardando processamento.")
        return
    df = pd.DataFrame(res)
    mc = ['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make']
    fin = df[df['tipo']=='financeiro']; base = df[df['tipo']=='base']
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Receita Total", f"R$ {df[mc].sum().sum():,.0f}")
    c2.metric("Ativos", f"{int(fin['ativos'].sum()):,}")
    c3.metric("Atividade Média", f"{fin['pct_atividade'].mean():.1f}%")
    c4.metric("Multimarcas Média", f"{fin['pct_multimarcas'].mean():.1f}%")
    st.markdown("---")
    st.markdown("### 🎯 IAF por Grupo")
    cb,cf = st.columns(2)
    for col,grupo,label in [(cb,base,"Base"),(cf,fin,"Financeiro")]:
        iaf_m = grupo['iaf'].mean() if len(grupo)>0 else 0
        cor = "#4CAF50" if iaf_m>=95 else ("#FFC107" if iaf_m>=85 else "#F44336")
        col.markdown(f"""<div style="text-align:center;padding:20px;border-radius:12px;border:2px solid {cor}">
            <div style="font-size:36px;font-weight:700;color:{cor}">{iaf_m:.1f}%</div>
            <div style="font-size:13px;color:#666">IAF Médio — {label}</div></div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🏅 Classificações")
    ordem = ['Diamante','Ouro','Prata','Bronze','Não Classificado']
    cc = df['classificacao'].value_counts().reindex(ordem,fill_value=0).reset_index()
    cc.columns = ['Classificação','Quantidade']
    fig = px.bar(cc, x='Classificação', y='Quantidade', color='Classificação',
                 color_discrete_map={c:cor_class(c) for c in ordem}, category_orders={'Classificação':ordem})
    fig.update_layout(showlegend=False, height=260, margin=dict(t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")
    st.markdown("### 📦 Receita por Marca")
    rm = {'Boticário':df['valor_boticario'].sum(),'Eudora':df['valor_eudora'].sum(),
          'OUI':df['valor_oui'].sum(),'QDB':df['valor_qdb'].sum(),
          'Cabelos':df['valor_cabelos'].sum(),'Make B.':df['valor_make'].sum()}
    dfm = pd.DataFrame([(k,v) for k,v in rm.items() if v>0], columns=['Marca','Receita'])
    fig2 = px.bar(dfm, x='Marca', y='Receita', color_discrete_sequence=['#1565C0'])
    fig2.update_layout(height=300, margin=dict(t=10,b=10))
    fig2.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
    st.plotly_chart(fig2, use_container_width=True)

def pg_base():
    st.markdown("## 👥 Supervisoras de Base")
    st.markdown("---")
    ciclo = get_ciclo_ativo()
    if not ciclo: st.warning("⚠️ Sem ciclo ativo."); return
    ciclos = get_ciclos(); nomes = [c['nome'] for c in ciclos]
    sel = st.selectbox("Ciclo", nomes, index=nomes.index(ciclo['nome']) if ciclo['nome'] in nomes else 0)
    cs = next((c for c in ciclos if c['nome']==sel), ciclo)
    sb_list = get_setores(tipo='base')
    if not sb_list: st.info("Nenhum setor Base configurado."); return
    res = get_resultados(cs['id'], tipo='base')
    metas = {m['setor_id']:m for m in get_metas(cs['id'])}
    res_d = {r['setor_id']:r for r in res}
    t_meta = sum(int(metas.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in sb_list)
    t_real = sum(int(metas.get(s['id'],{}).get('realizado_inicios_reinicios',0)) for s in sb_list)
    termometro(t_real, t_meta, "🎯 Meta do Grupo — Inícios + Reinícios")
    if t_meta>0 and t_real>=t_meta: st.success("✅ Meta do grupo atingida! +200 pontos.")
    else: st.error(f"❌ Meta não atingida. Faltam {t_meta-t_real}.")
    st.markdown("---")
    c_ant = next((c for c in ciclos if c['id']<cs['id']), None)
    r_ant = {r['setor_id']:r for r in get_resultados(c_ant['id'],tipo='base')} if c_ant else {}
    st.markdown("### 📋 Desempenho Individual")
    for s in sb_list:
        r = res_d.get(s['id']); meta = metas.get(s['id'],{})
        if not r: st.markdown(f"**{s['nome']}** — sem dados"); continue
        delta = round(r['iaf']-r_ant[s['id']]['iaf'],1) if s['id'] in r_ant else None
        c1,c2 = st.columns([1,2])
        with c1: card_iaf(s['nome'],r['iaf'],r['classificacao'],r['pontuacao_obtida'],r['pontuacao_maxima'],delta)
        with c2: semaforo(int(meta.get('realizado_inicios_reinicios',0)),int(meta.get('meta_inicios_reinicios',0)),"Inícios + Reinícios")
        st.markdown("---")
    if res:
        sid_nm = {s['id']:s['nome'] for s in sb_list}
        st.markdown("### 🏆 Ranking")
        dados = [{'Supervisora':sid_nm.get(r['setor_id'],str(r['setor_id'])),'IAF':r['iaf'],'Classificação':r['classificacao']} for r in res]
        df_r = pd.DataFrame(dados).sort_values('IAF',ascending=True)
        fig = go.Figure(go.Bar(x=df_r['IAF'],y=df_r['Supervisora'],orientation='h',
                               marker_color=[cor_class(c) for c in df_r['Classificação']],
                               text=[f"{v:.1f}%" for v in df_r['IAF']],textposition='outside'))
        fig.update_layout(height=max(200,len(dados)*60),margin=dict(t=10,b=10))
        for v,l in [(65,"Bronze"),(75,"Prata"),(85,"Ouro"),(95,"Diamante")]:
            fig.add_vline(x=v,line_dash="dot",annotation_text=l)
        st.plotly_chart(fig,use_container_width=True)
        st.markdown("### 📈 Evolução IAF")
        evol = []
        for c in ciclos[-6:]:
            for r in get_resultados(c['id'],tipo='base'):
                evol.append({'Ciclo':c['nome'],'Supervisora':sid_nm.get(r['setor_id'],str(r['setor_id'])),'IAF':r['iaf']})
        if evol:
            fig2 = px.line(pd.DataFrame(evol),x='Ciclo',y='IAF',color='Supervisora',markers=True)
            fig2.update_layout(height=300,margin=dict(t=10,b=10))
            st.plotly_chart(fig2,use_container_width=True)

def pg_financeiro():
    st.markdown("## 💼 Supervisoras de Financeiro")
    st.markdown("---")
    ciclo = get_ciclo_ativo()
    if not ciclo: st.warning("⚠️ Sem ciclo ativo."); return
    ciclos = get_ciclos(); nomes = [c['nome'] for c in ciclos]
    sel = st.selectbox("Ciclo", nomes, index=nomes.index(ciclo['nome']) if ciclo['nome'] in nomes else 0)
    cs = next((c for c in ciclos if c['nome']==sel), ciclo)
    sf_list = get_setores(tipo='financeiro')
    if not sf_list: st.info("Nenhum setor Financeiro configurado."); return
    res = get_resultados(cs['id'],tipo='financeiro')
    metas = {m['setor_id']:m for m in get_metas(cs['id'])}
    res_d = {r['setor_id']:r for r in res}
    c_ant = next((c for c in ciclos if c['id']<cs['id']),None)
    r_ant = {r['setor_id']:r for r in get_resultados(c_ant['id'],tipo='financeiro')} if c_ant else {}
    sid_nm = {s['id']:s['nome'] for s in sf_list}
    if r_ant:
        st.markdown("### 🏆 Ranking — Ciclo Anterior")
        dados_r = [{'Supervisora':s['nome'],'IAF':r_ant[s['id']]['iaf'],'Classificação':r_ant[s['id']]['classificacao']} for s in sf_list if s['id'] in r_ant]
        if dados_r:
            dfr = pd.DataFrame(dados_r).sort_values('IAF',ascending=False)
            fig = go.Figure(go.Bar(x=dfr['Supervisora'],y=dfr['IAF'],marker_color=[cor_class(c) for c in dfr['Classificação']],
                                   text=[f"{v:.1f}%" for v in dfr['IAF']],textposition='outside'))
            fig.update_layout(height=280,margin=dict(t=10,b=10))
            st.plotly_chart(fig,use_container_width=True)
        st.markdown("---")
    st.markdown("### 📋 Desempenho Individual")
    for s in sf_list:
        r = res_d.get(s['id']); meta = metas.get(s['id'],{})
        if not r: st.markdown(f"**{s['nome']}** — sem dados"); continue
        delta = round(r['iaf']-r_ant[s['id']]['iaf'],1) if s['id'] in r_ant else None
        with st.expander(f"**{s['nome']}** — IAF: {r['iaf']:.1f}% | {r['classificacao']}", expanded=True):
            c1,c2 = st.columns([1,2])
            with c1: card_iaf(s['nome'],r['iaf'],r['classificacao'],r['pontuacao_obtida'],r['pontuacao_maxima'],delta)
            with c2:
                st.markdown("**Receitas**")
                for cv,cm,lb,em in MARCAS_CFG:
                    v=r.get(cv,0); m=float(meta.get(cm,0))
                    if m>0 or v>0: semaforo(v,m,f"{em} {lb}","moeda")
                st.markdown("**Percentuais**")
                for cv,cm,lb in INDS_PCT:
                    v=r.get(cv,0); m=float(meta.get(cm,0))
                    if m>0 or v>0: semaforo(v,m,lb,"pct")
                st.markdown(f"<div style='font-size:12px;color:#999'>👥 Ativos: {r.get('ativos',0)} / Base: {int(meta.get('tamanho_base',0))}</div>",unsafe_allow_html=True)
    if res:
        st.markdown("---")
        st.markdown("### 📊 Receita por Marca")
        dados_b = []
        for r in res:
            nm = sid_nm.get(r['setor_id'],str(r['setor_id']))
            for cv,_,lb,_ in MARCAS_CFG:
                if r.get(cv,0)>0: dados_b.append({'Supervisora':nm,'Marca':lb,'Valor':r.get(cv,0)})
        if dados_b:
            fig2 = px.bar(pd.DataFrame(dados_b),x='Supervisora',y='Valor',color='Marca',barmode='stack')
            fig2.update_layout(height=350,margin=dict(t=10,b=10)); fig2.update_yaxes(tickprefix="R$ ",tickformat=",.0f")
            st.plotly_chart(fig2,use_container_width=True)
        st.markdown("### 🗺️ Heatmap")
        inds_h = ['Boticário','Eudora','OUI','QDB','Cabelos','Make','Multimarcas','Atividade']
        cvs = ['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make','pct_multimarcas','pct_atividade']
        cms = ['meta_boticario','meta_eudora','meta_oui','meta_qdb','meta_cabelos','meta_make','meta_multimarcas','meta_atividade']
        sups,mat,txt = [],[],[]
        for r in res:
            sups.append(sid_nm.get(r['setor_id'],str(r['setor_id']))); meta=metas.get(r['setor_id'],{}); ln,lt=[],[]
            for cv,cm in zip(cvs,cms):
                v=r.get(cv,0); m=float(meta.get(cm,0)); p=min(v/m*100 if m>0 else 0,150)
                ln.append(p); lt.append(f"{p:.0f}%")
            mat.append(ln); txt.append(lt)
        if mat:
            fig3 = go.Figure(go.Heatmap(z=mat,x=inds_h,y=sups,text=txt,texttemplate="%{text}",
                colorscale=[[0,'#F44336'],[0.475,'#FFC107'],[0.667,'#4CAF50'],[1,'#1565C0']],zmin=0,zmax=150))
            fig3.update_layout(height=max(200,len(sups)*50+100),margin=dict(t=10,b=10))
            st.plotly_chart(fig3,use_container_width=True)
        st.markdown("### 📈 Evolução IAF")
        evol = []
        for c in ciclos[-6:]:
            for r in get_resultados(c['id'],tipo='financeiro'):
                evol.append({'Ciclo':c['nome'],'Supervisora':sid_nm.get(r['setor_id'],str(r['setor_id'])),'IAF':r['iaf']})
        if evol:
            fig4 = px.line(pd.DataFrame(evol),x='Ciclo',y='IAF',color='Supervisora',markers=True)
            fig4.update_layout(height=300,margin=dict(t=10,b=10)); st.plotly_chart(fig4,use_container_width=True)

def pg_coordenadora():
    requer_perfil("gerencia")
    st.markdown("## 🏪 Painel da Coordenadora — ER")
    st.markdown("---")
    ciclo = get_ciclo_ativo()
    if not ciclo: st.warning("⚠️ Sem ciclo ativo."); return
    ciclos = get_ciclos(); nomes = [c['nome'] for c in ciclos]
    sel = st.selectbox("Ciclo", nomes, index=nomes.index(ciclo['nome']) if ciclo['nome'] in nomes else 0)
    cs = next((c for c in ciclos if c['nome']==sel),ciclo)
    meta_nm = float(get_config('meta_nao_multimarca_caixa',30))
    res = get_resultados_er(cs['id'])
    if not res: st.info("📊 Sem dados ER."); return
    df = pd.DataFrame(res)
    tp=df['total_pedidos'].sum(); tnm=df['pedidos_nao_multimarca'].sum()
    pg=tnm/tp*100 if tp>0 else 0; ac=len(df[df['pct_nao_multimarca']>meta_nm])
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total Pedidos",f"{tp:,}"); c2.metric("Não Multimarca",f"{tnm:,}")
    c3.metric("% Não Multimarca",f"{'🔴' if pg>meta_nm else '🟢'} {pg:.1f}%")
    c4.metric("Caixas Acima Meta",f"{ac}/{len(df)}")
    st.markdown("---"); st.markdown("### 🏷️ Ranking dos Caixas")
    for _,row in df.iterrows():
        p=row['pct_nao_multimarca']
        cor="#F44336" if p>meta_nm else ("#FFC107" if p>meta_nm*0.9 else "#4CAF50")
        ic="🔴" if p>meta_nm else ("🟡" if p>meta_nm*0.9 else "🟢")
        br=min(p/meta_nm*100 if meta_nm>0 else 0,100)
        st.markdown(f"""<div style="border-left:4px solid {cor};background:#f9f9f9;border-radius:6px;padding:12px 16px;margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:600">{ic} {row['usuario_finalizacao']}</span>
                <span style="font-weight:700;color:{cor}">{p:.1f}% não multimarca</span>
            </div>
            <div style="font-size:12px;color:#999;margin-top:4px">{row['pedidos_nao_multimarca']} de {row['total_pedidos']} | Meta ≤{meta_nm:.0f}%</div>
            <div style="background:#eee;border-radius:4px;height:6px;margin-top:8px;overflow:hidden">
                <div style="background:{cor};width:{br:.0f}%;height:100%"></div></div>
        </div>""",unsafe_allow_html=True)
    st.markdown("---"); st.markdown("### 📊 Comparativo")
    fig=go.Figure(go.Bar(x=df['usuario_finalizacao'],y=df['pct_nao_multimarca'],
        marker_color=['#F44336' if p>meta_nm else '#4CAF50' for p in df['pct_nao_multimarca']],
        text=[f"{p:.1f}%" for p in df['pct_nao_multimarca']],textposition='outside'))
    fig.add_hline(y=meta_nm,line_dash="dash",line_color="#FF9800",annotation_text=f"Meta {meta_nm:.0f}%")
    fig.update_layout(height=360,margin=dict(t=10,b=10)); fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig,use_container_width=True)
    evol=[]
    for c in ciclos[-6:]:
        for r in get_resultados_er(c['id']):
            evol.append({'Ciclo':c['nome'],'Caixa':r['usuario_finalizacao'],'% Não Multimarca':r['pct_nao_multimarca']})
    if evol:
        st.markdown("### 📈 Evolução")
        fig2=px.line(pd.DataFrame(evol),x='Ciclo',y='% Não Multimarca',color='Caixa',markers=True)
        fig2.add_hline(y=meta_nm,line_dash="dash",annotation_text="Meta")
        fig2.update_layout(height=300,margin=dict(t=10,b=10)); st.plotly_chart(fig2,use_container_width=True)

def pg_config():
    requer_perfil("gerencia")
    st.markdown("## ⚙️ Configurações")
    aba=st.radio("",["Setores","Pontuação & IAF","Ciclos & Metas","Upload","Senhas","Logs"],horizontal=True)
    st.markdown("---")
    sb=get_supabase(); usuario=st.session_state.get('usuario','sistema')
    if aba=="Setores":
        st.markdown("### 🗂️ Setores")
        with st.expander("➕ Novo setor"):
            nn=st.text_input("Nome"); tn=st.selectbox("Tipo",["financeiro","base"])
            if st.button("Adicionar"):
                if nn: sb.table("setores").insert({"nome":nn,"tipo":tn,"ativo":True}).execute(); st.success("Adicionado!"); st.rerun()
        for s in sb.table("setores").select("*").order("nome").execute().data or []:
            c1,c2,c3,c4=st.columns([3,2,2,1])
            c1.markdown(f"**{s['nome']}**")
            with c2: ti=st.selectbox("Tipo",["financeiro","base"],index=0 if s['tipo']=='financeiro' else 1,key=f"t{s['id']}")
            with c3: at=st.selectbox("Status",["Ativo","Inativo"],index=0 if s['ativo'] else 1,key=f"a{s['id']}")
            with c4:
                if st.button("💾",key=f"s{s['id']}"): sb.table("setores").update({"tipo":ti,"ativo":at=="Ativo"}).eq("id",s['id']).execute(); st.success("✓"); st.rerun()
    elif aba=="Pontuação & IAF":
        st.markdown("### 🎯 Pontuação e IAF")
        c1,c2=st.columns(2)
        with c1:
            pts_ir=st.number_input("Pts I+R",value=int(get_config('pts_inicios_reinicios',800)),step=50)
            pts_g=st.number_input("Pts Grupo",value=int(get_config('pts_meta_grupo',200)),step=50)
            pts_m=st.number_input("Pts/Marca",value=int(get_config('pts_por_marca_receita',100)),step=10)
            pts_mu=st.number_input("Pts Multimarcas",value=int(get_config('pts_multimarcas',100)),step=10)
            pts_c=st.number_input("Pts Cabelos%",value=int(get_config('pts_pct_cabelos',100)),step=10)
            pts_mk=st.number_input("Pts Make%",value=int(get_config('pts_pct_make',100)),step=10)
            pts_a=st.number_input("Pts Atividade",value=int(get_config('pts_atividade',100)),step=10)
        with c2:
            f50=st.number_input("≥X%=50pts",value=int(get_config('faixa_pontuacao_50pct',85)))
            f75=st.number_input("≥X%=75pts",value=int(get_config('faixa_pontuacao_75pct',95)))
            f100=st.number_input("≥X%=100pts",value=int(get_config('faixa_pontuacao_100pct',100)))
            br=st.number_input("Bronze≥",value=int(get_config('faixa_bronze_min',65)))
            pr=st.number_input("Prata≥",value=int(get_config('faixa_prata_min',75)))
            ou=st.number_input("Ouro≥",value=int(get_config('faixa_ouro_min',85)))
            di=st.number_input("Diamante≥",value=int(get_config('faixa_diamante_min',95)))
            mc=st.number_input("Meta% não-multi caixa",value=float(get_config('meta_nao_multimarca_caixa',30)))
        if st.button("💾 Salvar",use_container_width=True):
            for k,v in [('pts_inicios_reinicios',pts_ir),('pts_meta_grupo',pts_g),('pts_por_marca_receita',pts_m),
                        ('pts_multimarcas',pts_mu),('pts_pct_cabelos',pts_c),('pts_pct_make',pts_mk),('pts_atividade',pts_a),
                        ('faixa_pontuacao_50pct',f50),('faixa_pontuacao_75pct',f75),('faixa_pontuacao_100pct',f100),
                        ('faixa_bronze_min',br),('faixa_prata_min',pr),('faixa_ouro_min',ou),('faixa_diamante_min',di),
                        ('meta_nao_multimarca_caixa',mc)]:
                set_config(k,str(v),usuario)
            st.success("✅ Salvo!")
    elif aba=="Ciclos & Metas":
        st.markdown("### 📅 Ciclos")
        with st.expander("➕ Novo ciclo"):
            nc=st.text_input("Nome (ex: 05/2026)"); d1,d2=st.columns(2)
            di=d1.date_input("Início"); df_c=d2.date_input("Fim")
            if st.button("Criar"):
                if nc: sb.table("ciclos").insert({"nome":nc,"data_inicio":str(di),"data_fim":str(df_c),"ativo":True}).execute(); st.success("Criado!"); st.rerun()
        for c in get_ciclos():
            cc1,cc2,cc3=st.columns([3,2,2])
            cc1.markdown(f"**{c['nome']}**"); cc2.markdown("✅ Ativo" if c['ativo'] else "⬜ Inativo")
            if not c['ativo']:
                with cc3:
                    if st.button("Ativar",key=f"at{c['id']}"):
                        sb.table("ciclos").update({"ativo":False}).execute()
                        sb.table("ciclos").update({"ativo":True}).eq("id",c['id']).execute(); st.rerun()
        st.markdown("---"); st.markdown("### 🎯 Metas do Período")
        ca=get_ciclo_ativo()
        if not ca: st.warning("Crie um ciclo ativo."); return
        st.info(f"Ciclo: **{ca['nome']}**")
        setores=get_setores(); mex={m['setor_id']:m for m in get_metas(ca['id'])}
        tb,tf=st.tabs(["Base","Financeiro"])
        with tb:
            for s in [x for x in setores if x['tipo']=='base']:
                st.markdown(f"**{s['nome']}**"); ma=mex.get(s['id'],{})
                b1,b2=st.columns(2)
                mir=b1.number_input("Meta I+R",min_value=0,value=int(ma.get('meta_inicios_reinicios',0)),key=f"mir{s['id']}")
                rir=b2.number_input("Realizado I+R",min_value=0,value=int(ma.get('realizado_inicios_reinicios',0)),key=f"rir{s['id']}")
                if st.button("💾",key=f"sb{s['id']}"): upsert_meta(ca['id'],s['id'],{'meta_inicios_reinicios':mir,'realizado_inicios_reinicios':rir,'updated_by':usuario}); st.success("Salvo!")
                st.markdown("---")
        with tf:
            for s in [x for x in setores if x['tipo']=='financeiro']:
                st.markdown(f"**{s['nome']}**"); ma=mex.get(s['id'],{})
                f1,f2,f3=st.columns(3)
                with f1:
                    st.markdown("*R$*")
                    mbo=st.number_input("Boticário",min_value=0.0,value=float(ma.get('meta_boticario',0)),key=f"mb{s['id']}")
                    meu=st.number_input("Eudora",min_value=0.0,value=float(ma.get('meta_eudora',0)),key=f"me{s['id']}")
                    mou=st.number_input("OUI",min_value=0.0,value=float(ma.get('meta_oui',0)),key=f"mo{s['id']}")
                    mqd=st.number_input("QDB",min_value=0.0,value=float(ma.get('meta_qdb',0)),key=f"mq{s['id']}")
                    mca=st.number_input("Cabelos R$",min_value=0.0,value=float(ma.get('meta_cabelos',0)),key=f"mc{s['id']}")
                    mma=st.number_input("Make R$",min_value=0.0,value=float(ma.get('meta_make',0)),key=f"mm{s['id']}")
                with f2:
                    st.markdown("*%*")
                    mmu=st.number_input("Multimarcas%",0.0,100.0,float(ma.get('meta_multimarcas',0)),key=f"mmu{s['id']}")
                    mpc=st.number_input("Cabelos%",0.0,100.0,float(ma.get('meta_pct_cabelos',0)),key=f"mpc{s['id']}")
                    mpm=st.number_input("Make%",0.0,100.0,float(ma.get('meta_pct_make',0)),key=f"mpm{s['id']}")
                    mat=st.number_input("Atividade%",0.0,100.0,float(ma.get('meta_atividade',0)),key=f"mat{s['id']}")
                with f3:
                    st.markdown("*Base*")
                    mtb=st.number_input("Tamanho Base",0,value=int(ma.get('tamanho_base',0)),key=f"mtb{s['id']}")
                if st.button("💾",key=f"sf{s['id']}"):
                    upsert_meta(ca['id'],s['id'],{'meta_boticario':mbo,'meta_eudora':meu,'meta_oui':mou,'meta_qdb':mqd,
                        'meta_cabelos':mca,'meta_make':mma,'meta_multimarcas':mmu,'meta_pct_cabelos':mpc,
                        'meta_pct_make':mpm,'meta_atividade':mat,'tamanho_base':mtb,'updated_by':usuario})
                    st.success("Salvo!")
                st.markdown("---")
    elif aba=="Upload":
        requer_perfil("admin")
        st.markdown("### 📤 Upload de Planilhas")
        ca=get_ciclo_ativo()
        if not ca: st.warning("Sem ciclo ativo."); return
        st.info(f"Ciclo: **{ca['nome']}**")
        uploaded={}; c1u,c2u=st.columns(2)
        for i,nm in enumerate(ARQS):
            with (c1u if i%2==0 else c2u):
                f=st.file_uploader(f"📁 {nm}.xlsx",type=['xlsx'],key=f"up{nm}")
                if f: uploaded[nm]=f
        if uploaded and st.button("🚀 Processar",use_container_width=True,type="primary"):
            with st.spinner("Processando..."):
                try:
                    dfs={}
                    for nm,arq in uploaded.items():
                        dfs[nm]=pd.read_excel(arq) if nm in ['ER','Ativos'] else ler_planilha(arq,nm)
                    cfg={r['chave']:r['valor'] for r in (sb.table("configuracoes").select("chave,valor").execute().data or [])}
                    res_p=processar_ciclo(dfs,get_metas(ca['id']),get_setores(),cfg)
                    for r in res_p['resultados']:
                        r['ciclo_id']=ca['id']; sb.table("resultados").upsert(r,on_conflict="ciclo_id,setor_id").execute()
                    for r in res_p['resultados_er']:
                        r['ciclo_id']=ca['id']; sb.table("resultados_er").upsert(r,on_conflict="ciclo_id,usuario_finalizacao").execute()
                    for nm in uploaded: log_upload(ca['id'],nm,usuario)
                    st.success(f"✅ {len(uploaded)} arquivo(s) processados!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    elif aba=="Senhas":
        requer_perfil("admin")
        st.markdown("### 🔑 Senhas")
        st.warning("Alterar senhas afeta todos os usuários.")
        s1,s2,s3=st.columns(3)
        with s1:
            st.markdown("**Leitura**"); nl=st.text_input("Nova",type="password",key="nl")
            if st.button("Alterar",key="al"):
                if nl: set_config('senha_leitura',nl,usuario); st.success("✓")
        with s2:
            st.markdown("**Gerência**"); ng=st.text_input("Nova",type="password",key="ng")
            if st.button("Alterar",key="ag"):
                if ng: set_config('senha_gerencia',ng,usuario); st.success("✓")
        with s3:
            st.markdown("**Admin**"); na=st.text_input("Nova",type="password",key="na")
            if st.button("Alterar",key="aa"):
                if na: set_config('senha_admin',na,usuario); st.success("✓")
    elif aba=="Logs":
        st.markdown("### 📋 Logs")
        tl1,tl2=st.tabs(["Uploads","Alterações"])
        with tl1:
            ca=get_ciclo_ativo()
            if ca:
                logs=get_logs_upload(ca['id'])
                if logs:
                    dl=pd.DataFrame(logs); dl['data_upload']=pd.to_datetime(dl['data_upload']).dt.strftime('%d/%m/%Y %H:%M')
                    st.dataframe(dl[['arquivo','usuario','data_upload']],use_container_width=True)
                else: st.info("Sem uploads.")
        with tl2:
            r=sb.table("log_alteracoes").select("*").order("created_at",desc=True).limit(50).execute()
            if r.data:
                dla=pd.DataFrame(r.data); dla['created_at']=pd.to_datetime(dla['created_at']).dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(dla[['tabela','campo','valor_anterior','valor_novo','usuario','created_at']],use_container_width=True)
            else: st.info("Sem alterações.")

# MAIN
check_auth()
if not st.session_state.get("perfil"):
    login_screen()
else:
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.usuario}**")
        st.markdown(f"🔑 `{st.session_state.perfil}`")
        st.markdown("---")
        pg=st.radio("Navegação",["🏠 Home","👥 Base","💼 Financeiro","🏪 Coordenadora","⚙️ Configurações"])
        st.markdown("---")
        if st.button("🚪 Sair",use_container_width=True):
            st.session_state.perfil=None; st.session_state.usuario=None; st.rerun()
    if pg=="🏠 Home": pg_home()
    elif pg=="👥 Base": pg_base()
    elif pg=="💼 Financeiro": pg_financeiro()
    elif pg=="🏪 Coordenadora": pg_coordenadora()
    elif pg=="⚙️ Configurações": pg_config()
