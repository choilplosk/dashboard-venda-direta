import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Venda Direta", page_icon="💼", layout="wide")

st.markdown("""<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="metric-container"] { background: white; border-radius:10px; padding:12px; border:1px solid #eee; }
    .stRadio > div { gap: 0.5rem; }
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
    existing = sb.table("configuracoes").select("id").eq("chave", chave).execute()
    if existing.data:
        sb.table("configuracoes").update({"valor": str(valor), "updated_by": usuario}).eq("chave", chave).execute()
    else:
        sb.table("configuracoes").insert({"chave": chave, "valor": str(valor), "updated_by": usuario}).execute()
    try:
        sb.table("log_alteracoes").insert({"tabela": "configuracoes", "campo": chave,
            "valor_anterior": str(old), "valor_novo": str(valor), "usuario": usuario}).execute()
    except:
        pass

def get_ciclos():
    return get_supabase().table("ciclos").select("*").order("id", desc=True).execute().data or []

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

# Formatação numérica BR
def fmt_br(valor, decimais=2):
    if isinstance(valor, float) or isinstance(valor, int):
        return f"{valor:_.{decimais}f}".replace("_", "X").replace(".", ",").replace("X", ".")
    return str(valor)

def fmt_moeda(valor):
    return f"R$ {fmt_br(valor)}"

def fmt_pct(valor, decimais=1):
    return f"{valor:.{decimais}f}%".replace(".", ",")

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

# =============================================
# COMPONENTES VISUAIS
# =============================================
def kpi_grande(label, valor, subtexto=None, cor="#1565C0"):
    sub = f'<div style="font-size:12px;color:#888;margin-top:6px">{subtexto}</div>' if subtexto else ""
    html = (
        f'<div style="background:white;border-radius:12px;padding:20px;border:1px solid #eee;text-align:center">'
        f'<div style="font-size:12px;color:#999;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">{label}</div>'
        f'<div style="font-size:32px;font-weight:700;color:{cor}">{valor}</div>'
        f'{sub}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def semaforo_simples(pct, label, realizado_str, meta_str):
    cor = "#9E9E9E" if pct==0 else ("#4CAF50" if pct>=100 else ("#FFC107" if pct>=95 else "#F44336"))
    ic = "⚪" if pct==0 else ("🟢" if pct>=100 else ("🟡" if pct>=95 else "🔴"))
    pct_str = f"{pct:.0f}%" if pct > 0 else "—"
    return (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:8px 0;border-bottom:1px solid #f0f0f0">'
        f'<span style="font-size:13px;color:#555">{ic} {label}</span>'
        f'<div style="text-align:right">'
        f'<span style="font-size:13px;font-weight:600;color:{cor}">{realizado_str}</span>'
        f'<span style="font-size:11px;color:#aaa"> / {meta_str}</span>'
        f'<br><span style="font-size:11px;color:{cor};font-weight:600">{pct_str} da meta</span>'
        f'</div></div>'
    )

def linha_ranking(pos, nome, iaf, cl, delta=None, extra=None):
    cor = cor_class(cl)
    em = emoji_class(cl)
    pos_cores = ["#F9A825","#9E9E9E","#A1887F"]
    pos_bg = pos_cores[pos-1] if pos <= 3 else "#f0f0f0"
    pos_txt = "white" if pos <= 3 else "#555"
    barra = min(iaf, 100)
    iaf_str = f"{iaf:.1f}%"
    html = (
        f'<div style="display:flex;align-items:center;gap:12px;padding:10px 12px;'
        f'background:white;border-radius:8px;border:1px solid #eee;margin-bottom:6px">'
        f'<div style="min-width:28px;height:28px;border-radius:50%;background:{pos_bg};'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-weight:700;font-size:13px;color:{pos_txt}">{pos}</div>'
        f'<div style="flex:1">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
        f'<span style="font-weight:600;font-size:14px">{nome}</span>'
        f'<div style="display:flex;align-items:center;gap:8px">'
    )
    if delta is not None:
        dc = "#4CAF50" if delta >= 0 else "#F44336"
        ds = ("▲" if delta >= 0 else "▼") + f"{abs(delta):.1f}%"
        html += f'<span style="font-size:11px;color:{dc}">{ds}</span>'
    html += (
        f'<span style="font-weight:700;font-size:16px;color:{cor}">{iaf_str}</span>'
        f'<span style="background:{cor};color:white;padding:2px 8px;border-radius:12px;font-size:11px">{em} {cl}</span>'
    )
    if extra:
        html += f'<span style="font-size:11px;color:#999">{extra}</span>'
    html += (
        f'</div></div>'
        f'<div style="background:#f0f0f0;border-radius:4px;height:6px;overflow:hidden">'
        f'<div style="background:{cor};width:{barra:.1f}%;height:100%;border-radius:4px"></div>'
        f'</div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

ARQS = ['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos','ER']
MARCAS_CFG = [('valor_boticario','meta_boticario','Boticário'),
              ('valor_eudora','meta_eudora','Eudora'),
              ('valor_oui','meta_oui','OUI'),
              ('valor_qdb','meta_qdb','QDB'),
              ('valor_cabelos','meta_cabelos','Cabelos'),
              ('valor_make','meta_make','Make B.')]
INDS_PCT = [('pct_multimarcas','meta_multimarcas','Multimarcas'),
            ('pct_cabelos','meta_pct_cabelos','Cabelos %'),
            ('pct_make','meta_pct_make','Make %'),
            ('pct_atividade','meta_atividade','Atividade')]

# =============================================
# PÁGINA HOME
# =============================================
def pg_home():
    ciclo = get_ciclo_ativo()
    if ciclo:
        st.markdown(f"## Visão Geral — Ciclo **{ciclo['nome']}**")
    else:
        st.markdown("## Visão Geral")
        st.warning("⚠️ Nenhum ciclo ativo. Configure em Configurações → Ciclos & Metas.")
        return
    st.markdown("---")

    res = get_resultados(ciclo['id'])
    if not res:
        st.info("📊 Aguardando processamento dos dados do ciclo.")
        _status_arquivos(ciclo)
        return

    df = pd.DataFrame(res)
    mc = ['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make']
    fin = df[df['tipo']=='financeiro']
    base = df[df['tipo']=='base']
    receita_total = df[mc].sum().sum()
    total_ativos = int(fin['ativos'].sum())
    pct_ativ = fin['pct_atividade'].mean() if len(fin) > 0 else 0
    pct_multi = fin['pct_multimarcas'].mean() if len(fin) > 0 else 0

    # KPIs grandes
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_grande("Receita Total", fmt_moeda(receita_total))
    with c2: kpi_grande("Revendedores Ativos", f"{total_ativos:,}".replace(",","."))
    with c3: kpi_grande("Atividade Média", fmt_pct(pct_ativ), cor="#4CAF50" if pct_ativ>=80 else "#F44336")
    with c4: kpi_grande("Multimarcas Média", fmt_pct(pct_multi), cor="#4CAF50" if pct_multi>=50 else "#F44336")

    st.markdown("---")

    # IAF por grupo
    col_b, col_f = st.columns(2)
    iaf_base = base['iaf'].mean() if len(base) > 0 else 0
    iaf_fin = fin['iaf'].mean() if len(fin) > 0 else 0
    with col_b:
        cor = "#4CAF50" if iaf_base>=95 else ("#FFC107" if iaf_base>=85 else "#F44336")
        kpi_grande("IAF Médio — Base", fmt_pct(iaf_base), cor=cor)
    with col_f:
        cor = "#4CAF50" if iaf_fin>=95 else ("#FFC107" if iaf_fin>=85 else "#F44336")
        kpi_grande("IAF Médio — Financeiro", fmt_pct(iaf_fin), cor=cor)

    st.markdown("---")

    # Pódio top 3
    st.markdown("### 🏆 Pódio do Ciclo")
    sb = get_supabase()
    todos = df.sort_values('iaf', ascending=False).head(3)
    cols_podio = st.columns(3)
    for i, (_, r) in enumerate(todos.iterrows()):
        try:
            sn = sb.table("setores").select("nome").eq("id", int(r['setor_id'])).single().execute()
            nm = sn.data['nome'] if sn.data else "—"
        except:
            nm = "—"
        with cols_podio[i]:
            pos_emoji = ["🥇","🥈","🥉"][i]
            cor = cor_class(r['classificacao'])
            st.markdown(f"""<div style="text-align:center;padding:16px;border-radius:12px;border:2px solid {cor};background:white">
                <div style="font-size:28px">{pos_emoji}</div>
                <div style="font-weight:600;font-size:14px;margin:6px 0">{nm}</div>
                <div style="font-size:24px;font-weight:700;color:{cor}">{fmt_pct(r['iaf'])}</div>
                <div style="font-size:12px;color:#999">{emoji_class(r['classificacao'])} {r['classificacao']}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Tabela de classificações
    st.markdown("### 🏅 Classificações")
    # Filtrar apenas setores ativos
    try:
        slist = sb.table("setores").select("id,nome,ativo").execute().data or []
        nomes_map = {s['id']: s['nome'] for s in slist}
        ids_ativos_home = {s['id'] for s in slist if s['ativo']}
    except:
        nomes_map = {}
        ids_ativos_home = set()
    todos_res = df[df['setor_id'].isin(ids_ativos_home)].sort_values('iaf', ascending=False)

    for _, r in todos_res.iterrows():
        nm = nomes_map.get(r['setor_id'], str(r['setor_id']))
        cor = cor_class(r['classificacao'])
        em = emoji_class(r['classificacao'])
        st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;
            padding:10px 16px;border-radius:8px;border-left:4px solid {cor};
            background:white;border-top:1px solid #f5f5f5;border-right:1px solid #f5f5f5;
            border-bottom:1px solid #f5f5f5;margin-bottom:4px">
            <span style="font-size:14px;font-weight:500">{nm}</span>
            <div style="display:flex;align-items:center;gap:16px">
                <span style="font-size:12px;color:#999">{r['pontuacao_obtida']:.0f}/{r['pontuacao_maxima']:.0f} pts</span>
                <span style="font-size:16px;font-weight:700;color:{cor}">{fmt_pct(r['iaf'])}</span>
                <span style="background:{cor};color:white;padding:3px 10px;border-radius:12px;font-size:12px">{em} {r['classificacao']}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    _status_arquivos(ciclo)

def _status_arquivos(ciclo):
    st.markdown("### 📁 Status dos Arquivos")
    logs = get_logs_upload(ciclo['id'])
    arqs_ok = {l['arquivo'] for l in logs}
    arqs_data = {l['arquivo']:l['data_upload'] for l in logs}
    cols = st.columns(4)
    for i,a in enumerate(ARQS):
        ok = a in arqs_ok
        cor = "#4CAF50" if ok else "#F44336"
        info = arqs_data.get(a,"")[:16] if ok else "Aguardando"
        with cols[i%4]:
            st.markdown(f"""<div style="padding:8px 12px;border-radius:8px;border:1px solid {cor}33;
                background:{cor}11;margin-bottom:6px;font-size:12px">
                {"✅" if ok else "❌"} <b>{a}</b><br>
                <span style="color:{cor}">{info}</span>
            </div>""", unsafe_allow_html=True)
    falt = [a for a in ARQS if a not in arqs_ok]
    if falt:
        st.warning(f"⚠️ Pendentes: {', '.join(falt)}")
    else:
        st.success("✅ Todos os arquivos carregados!")

# =============================================
# PÁGINA BASE
# =============================================
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

    res_all = get_resultados(cs['id'], tipo='base')
    metas = {m['setor_id']:m for m in get_metas(cs['id'])}
    # Filtrar apenas setores ativos
    ids_ativos = {s['id'] for s in sb_list}
    res = [r for r in res_all if r['setor_id'] in ids_ativos]
    res_d = {r['setor_id']:r for r in res}
    sid_nm = {s['id']:s['nome'] for s in sb_list}

    t_meta = sum(int(metas.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in sb_list)
    t_real = sum(int(metas.get(s['id'],{}).get('realizado_inicios_reinicios',0)) for s in sb_list)

    # KPIs do grupo
    c1,c2,c3 = st.columns(3)
    pct_g = t_real/t_meta*100 if t_meta > 0 else 0
    cor_g = "#4CAF50" if pct_g>=100 else ("#FFC107" if pct_g>=95 else "#F44336")
    with c1: kpi_grande("Meta do Grupo", f"{t_real} / {t_meta}", f"{fmt_pct(pct_g)} atingido", cor=cor_g)
    grupo_batido = t_meta > 0 and t_real >= t_meta
    with c2: kpi_grande("Bônus Grupo", "✅ Conquistado" if grupo_batido else "❌ Não conquistado",
                         "+200 pts para todas" if grupo_batido else f"Faltam {t_meta-t_real}",
                         cor="#4CAF50" if grupo_batido else "#F44336")
    iaf_medio = sum(r['iaf'] for r in res)/len(res) if res else 0
    with c3: kpi_grande("IAF Médio do Grupo", fmt_pct(iaf_medio), cor=cor_class(class_iaf(iaf_medio,{})))

    st.markdown("---")

    # Ranking
    st.markdown("### 🏆 Ranking Individual")
    c_ant = next((c for c in ciclos if c['id']<cs['id']),None)
    r_ant = {r['setor_id']:r for r in get_resultados(c_ant['id'],tipo='base')} if c_ant else {}

    res_sorted = sorted(res, key=lambda x: x['iaf'], reverse=True)
    for pos, r in enumerate(res_sorted, 1):
        sid = r['setor_id']
        nome = sid_nm.get(sid, str(sid))
        meta = metas.get(sid,{})
        real_ir = int(meta.get('realizado_inicios_reinicios',0))
        meta_ir = int(meta.get('meta_inicios_reinicios',0))
        contrib = real_ir/t_meta*100 if t_meta > 0 else 0
        delta = round(r['iaf']-r_ant[sid]['iaf'],1) if sid in r_ant else None
        extra = f"I+R: {real_ir}/{meta_ir} | Contrib: {fmt_pct(contrib)}"
        linha_ranking(pos, nome, r['iaf'], r['classificacao'], delta, extra)

    st.markdown("---")

    # Gráfico contribuição para meta grupo
    st.markdown("### 📊 Contribuição para Meta do Grupo")
    if res and t_meta > 0:
        dados_contrib = []
        for r in res_sorted:
            sid = r['setor_id']
            meta = metas.get(sid,{})
            real_ir = int(meta.get('realizado_inicios_reinicios',0))
            dados_contrib.append({'Supervisora': sid_nm.get(sid,str(sid)), 'Contribuição': real_ir/t_meta*100, 'Realizado': real_ir})

        fig = go.Figure()
        cores_contrib = [cor_class(r['classificacao']) for r in res_sorted]
        for i, d in enumerate(dados_contrib):
            fig.add_trace(go.Bar(
                name=d['Supervisora'], x=[d['Contribuição']], y=['Grupo'],
                orientation='h', marker_color=cores_contrib[i],
                text=f"{d['Supervisora']}: {d['Realizado']} ({d['Contribuição']:.1f}%)",
                textposition='inside', insidetextanchor='middle', showlegend=True
            ))
        fig.add_vline(x=100, line_dash="dash", line_color="#333", annotation_text="Meta 100%")
        fig.update_layout(barmode='stack', height=120, margin=dict(t=10,b=10,l=10,r=10),
                         xaxis_title="% da Meta do Grupo", xaxis_ticksuffix="%",
                         legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="left", x=0))
        st.plotly_chart(fig, use_container_width=True)

    # Evolução IAF
    st.markdown("### 📈 Evolução do IAF")
    evol = []
    for c in ciclos[-6:]:
        for r in get_resultados(c['id'],tipo='base'):
            evol.append({'Ciclo':c['nome'],'Supervisora':sid_nm.get(r['setor_id'],str(r['setor_id'])),'IAF':r['iaf']})
    if evol:
        fig2 = px.line(pd.DataFrame(evol),x='Ciclo',y='IAF',color='Supervisora',markers=True)
        fig2.update_layout(height=300,margin=dict(t=10,b=10))
        fig2.update_yaxes(ticksuffix="%")
        for v,l in [(65,"Bronze"),(75,"Prata"),(85,"Ouro"),(95,"Diamante")]:
            fig2.add_hline(y=v,line_dash="dot",line_color=cor_class(l if l!="Bronze" else "Bronze"),
                          annotation_text=l,annotation_position="right")
        st.plotly_chart(fig2,use_container_width=True)

# =============================================
# PÁGINA FINANCEIRO
# =============================================
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

    res_all = get_resultados(cs['id'],tipo='financeiro')
    metas = {m['setor_id']:m for m in get_metas(cs['id'])}
    # Filtrar apenas setores ativos
    ids_ativos_fin = {s['id'] for s in sf_list}
    res = [r for r in res_all if r['setor_id'] in ids_ativos_fin]
    res_d = {r['setor_id']:r for r in res}
    # Buscar nomes de todos os setores para garantir mapeamento correto
    todos_setores = get_supabase().table("setores").select("id,nome").execute().data or []
    sid_nm = {s['id']:s['nome'] for s in todos_setores}

    c_ant = next((c for c in ciclos if c['id']<cs['id']),None)
    r_ant = {r['setor_id']:r for r in get_resultados(c_ant['id'],tipo='financeiro')} if c_ant else {}

    # KPIs consolidados do grupo
    if res:
        df_res = pd.DataFrame(res)
        receita_total = sum(df_res[c].sum() for c in ['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make'])
        total_ativos = int(df_res['ativos'].sum())
        iaf_medio = df_res['iaf'].mean()
        pct_multi_med = df_res['pct_multimarcas'].mean()
        pct_ativ_med = df_res['pct_atividade'].mean()

        # Calcular metas consolidadas do grupo
        meta_receita_total = sum(
            float(metas.get(s['id'],{}).get('meta_boticario',0)) +
            float(metas.get(s['id'],{}).get('meta_eudora',0)) +
            float(metas.get(s['id'],{}).get('meta_oui',0)) +
            float(metas.get(s['id'],{}).get('meta_qdb',0)) +
            float(metas.get(s['id'],{}).get('meta_cabelos',0)) +
            float(metas.get(s['id'],{}).get('meta_make',0))
            for s in sf_list
        )
        meta_multi_med = sum(float(metas.get(s['id'],{}).get('meta_multimarcas',0)) for s in sf_list) / len(sf_list) if sf_list else 0
        meta_ativ_med = sum(float(metas.get(s['id'],{}).get('meta_atividade',0)) for s in sf_list) / len(sf_list) if sf_list else 0

        pct_rec = receita_total/meta_receita_total*100 if meta_receita_total > 0 else 0
        pct_multi_cum = pct_multi_med/meta_multi_med*100 if meta_multi_med > 0 else 0
        pct_ativ_cum = pct_ativ_med/meta_ativ_med*100 if meta_ativ_med > 0 else 0

        def sub_meta(realizado_str, meta_str, pct_cum):
            cor = "#4CAF50" if pct_cum>=100 else ("#FFC107" if pct_cum>=95 else ("#F44336" if pct_cum>0 else "#999"))
            return f'Meta: {meta_str} <span style="color:{cor};font-weight:600">({pct_cum:.0f}%)</span>' if pct_cum > 0 else f'Meta: {meta_str}'

        st.markdown("### 📊 Visão do Grupo")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: kpi_grande("Receita Total", fmt_moeda(receita_total),
            subtexto=sub_meta("", fmt_moeda(meta_receita_total), pct_rec) if meta_receita_total>0 else None)
        with c2: kpi_grande("Ativos Total", f"{total_ativos:,}".replace(",","."))
        with c3: kpi_grande("IAF Médio", fmt_pct(iaf_medio), cor=cor_class(class_iaf(iaf_medio,{})))
        with c4: kpi_grande("Multimarcas Méd.", fmt_pct(pct_multi_med),
            subtexto=sub_meta("", fmt_pct(meta_multi_med), pct_multi_cum) if meta_multi_med>0 else None)
        with c5: kpi_grande("Atividade Méd.", fmt_pct(pct_ativ_med),
            subtexto=sub_meta("", fmt_pct(meta_ativ_med), pct_ativ_cum) if meta_ativ_med>0 else None)
        st.markdown("---")

        # Rankings por indicador
        st.markdown("### 🏆 Rankings por Indicador")
        tab_iaf, tab_multi, tab_ativ, tab_cab, tab_make = st.tabs(["IAF","Multimarcas","Atividade","Cabelos %","Make %"])

        def mini_ranking(dados_rank, ind_key, fmt="pct"):
            dados_rank = sorted(dados_rank, key=lambda x: x[ind_key], reverse=True)
            for pos, d in enumerate(dados_rank, 1):
                v = d[ind_key]
                m = d.get('meta_'+ind_key, 0)
                pct = v/m*100 if m>0 else 0
                cor = "#4CAF50" if pct>=100 else ("#FFC107" if pct>=95 else "#F44336")
                ic = "🟢" if pct>=100 else ("🟡" if pct>=95 else "🔴")
                vs = fmt_pct(v) if fmt=="pct" else fmt_moeda(v)
                ms = fmt_pct(m) if fmt=="pct" else fmt_moeda(m)
                pos_cor = ["#F9A825","#9E9E9E","#A1887F"]
                pb = pos_cor[pos-1] if pos<=3 else "#f0f0f0"
                pt = "white" if pos<=3 else "#555"
                st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
                    background:white;border-radius:8px;border:1px solid #eee;margin-bottom:4px">
                    <div style="min-width:24px;height:24px;border-radius:50%;background:{pb};
                        display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:{pt}">{pos}</div>
                    <span style="flex:1;font-size:13px;font-weight:500">{d['nome']}</span>
                    <span style="font-size:13px;font-weight:700;color:{cor}">{ic} {vs}</span>
                    <span style="font-size:11px;color:#aaa">meta {ms} ({pct:.0f}%)</span>
                </div>""", unsafe_allow_html=True)

        dados_rank_base = []
        for r in res:
            nm = sid_nm.get(r['setor_id'],str(r['setor_id']))
            meta = metas.get(r['setor_id'],{})
            dados_rank_base.append({
                'nome':nm,'iaf':r['iaf'],'classificacao':r['classificacao'],
                'pct_multimarcas':r['pct_multimarcas'],'meta_pct_multimarcas':float(meta.get('meta_multimarcas',0)),
                'pct_atividade':r['pct_atividade'],'meta_pct_atividade':float(meta.get('meta_atividade',0)),
                'pct_cabelos':r['pct_cabelos'],'meta_pct_cabelos':float(meta.get('meta_pct_cabelos',0)),
                'pct_make':r['pct_make'],'meta_pct_make':float(meta.get('meta_pct_make',0)),
            })

        with tab_iaf:
            res_sorted = sorted(res, key=lambda x: x['iaf'], reverse=True)
            for pos,r in enumerate(res_sorted,1):
                delta = round(r['iaf']-r_ant[r['setor_id']]['iaf'],1) if r['setor_id'] in r_ant else None
                linha_ranking(pos, sid_nm.get(r['setor_id'],str(r['setor_id'])), r['iaf'], r['classificacao'], delta)
        with tab_multi:
            mini_ranking(dados_rank_base, 'pct_multimarcas')
        with tab_ativ:
            mini_ranking(dados_rank_base, 'pct_atividade')
        with tab_cab:
            mini_ranking(dados_rank_base, 'pct_cabelos')
        with tab_make:
            mini_ranking(dados_rank_base, 'pct_make')

        st.markdown("---")

    # Desempenho individual com radar
    st.markdown("### 📋 Desempenho Individual")
    res_sorted_ind = sorted(res, key=lambda x: x['iaf'], reverse=True)
    for r in res_sorted_ind:
        sid = r['setor_id']
        nome = sid_nm.get(sid, str(sid))
        meta = metas.get(sid,{})
        delta = round(r['iaf']-r_ant[sid]['iaf'],1) if sid in r_ant else None
        cor = cor_class(r['classificacao'])
        em = emoji_class(r['classificacao'])
        delta_html = ""
        if delta is not None:
            sc = "#4CAF50" if delta>=0 else "#F44336"
            delta_html = f'<span style="font-size:12px;color:{sc}">{"▲" if delta>=0 else "▼"}{abs(delta):.1f}%</span>'

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"""<div style="border:2px solid {cor};border-radius:12px;padding:16px;background:white;height:100%">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <span style="font-weight:600;font-size:15px">{nome}</span>
                    <span style="background:{cor};color:white;padding:3px 10px;border-radius:12px;font-size:12px">{em} {r['classificacao']}</span>
                </div>
                <div style="text-align:center;margin:12px 0">
                    <span style="font-size:40px;font-weight:700;color:{cor}">{fmt_pct(r['iaf'])}</span>
                    <div style="font-size:12px;color:#999;margin-top:4px">IAF — {r['pontuacao_obtida']:.0f}/{r['pontuacao_maxima']:.0f} pts {delta_html}</div>
                </div>
                <div style="background:#f0f0f0;border-radius:6px;height:8px;overflow:hidden">
                    <div style="background:{cor};width:{min(r['iaf'],100):.1f}%;height:100%;border-radius:6px"></div>
                </div>
                <div style="margin-top:12px;font-size:12px">""" +
                semaforo_simples(
                    r['valor_boticario']/float(meta.get('meta_boticario',1))*100 if float(meta.get('meta_boticario',0))>0 else 0,
                    "Boticário", fmt_moeda(r['valor_boticario']), fmt_moeda(float(meta.get('meta_boticario',0)))
                ) +
                semaforo_simples(
                    r['valor_eudora']/float(meta.get('meta_eudora',1))*100 if float(meta.get('meta_eudora',0))>0 else 0,
                    "Eudora", fmt_moeda(r['valor_eudora']), fmt_moeda(float(meta.get('meta_eudora',0)))
                ) +
                semaforo_simples(
                    r['valor_oui']/float(meta.get('meta_oui',1))*100 if float(meta.get('meta_oui',0))>0 else 0,
                    "OUI", fmt_moeda(r['valor_oui']), fmt_moeda(float(meta.get('meta_oui',0)))
                ) +
                semaforo_simples(
                    r['valor_qdb']/float(meta.get('meta_qdb',1))*100 if float(meta.get('meta_qdb',0))>0 else 0,
                    "QDB", fmt_moeda(r['valor_qdb']), fmt_moeda(float(meta.get('meta_qdb',0)))
                ) +
                semaforo_simples(
                    r['valor_cabelos']/float(meta.get('meta_cabelos',1))*100 if float(meta.get('meta_cabelos',0))>0 else 0,
                    "Cabelos", fmt_moeda(r['valor_cabelos']), fmt_moeda(float(meta.get('meta_cabelos',0)))
                ) +
                semaforo_simples(
                    r['valor_make']/float(meta.get('meta_make',1))*100 if float(meta.get('meta_make',0))>0 else 0,
                    "Make B.", fmt_moeda(r['valor_make']), fmt_moeda(float(meta.get('meta_make',0)))
                ) +
                semaforo_simples(
                    r['pct_multimarcas']/float(meta.get('meta_multimarcas',1))*100 if float(meta.get('meta_multimarcas',0))>0 else 0,
                    "Multimarcas", fmt_pct(r['pct_multimarcas']), fmt_pct(float(meta.get('meta_multimarcas',0)))
                ) +
                semaforo_simples(
                    r['pct_atividade']/float(meta.get('meta_atividade',1))*100 if float(meta.get('meta_atividade',0))>0 else 0,
                    "Atividade", fmt_pct(r['pct_atividade']), fmt_pct(float(meta.get('meta_atividade',0)))
                ) +
                f"""</div></div>""", unsafe_allow_html=True)

        with col2:
            # Radar
            categorias = ['Boticário','Eudora','OUI','QDB','Cabelos','Make B.','Multimarcas','Atividade']
            vals_radar = [
                min(r['valor_boticario']/float(meta.get('meta_boticario',1))*100,150) if float(meta.get('meta_boticario',0))>0 else 0,
                min(r['valor_eudora']/float(meta.get('meta_eudora',1))*100,150) if float(meta.get('meta_eudora',0))>0 else 0,
                min(r['valor_oui']/float(meta.get('meta_oui',1))*100,150) if float(meta.get('meta_oui',0))>0 else 0,
                min(r['valor_qdb']/float(meta.get('meta_qdb',1))*100,150) if float(meta.get('meta_qdb',0))>0 else 0,
                min(r['valor_cabelos']/float(meta.get('meta_cabelos',1))*100,150) if float(meta.get('meta_cabelos',0))>0 else 0,
                min(r['valor_make']/float(meta.get('meta_make',1))*100,150) if float(meta.get('meta_make',0))>0 else 0,
                min(r['pct_multimarcas']/float(meta.get('meta_multimarcas',1))*100,150) if float(meta.get('meta_multimarcas',0))>0 else 0,
                min(r['pct_atividade']/float(meta.get('meta_atividade',1))*100,150) if float(meta.get('meta_atividade',0))>0 else 0,
            ]
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=vals_radar + [vals_radar[0]],
                theta=categorias + [categorias[0]],
                fill='toself',
                fillcolor='rgba(21,101,192,0.2)' if r['classificacao']=='Diamante' else (
                    'rgba(249,168,37,0.2)' if r['classificacao']=='Ouro' else (
                    'rgba(96,125,139,0.2)' if r['classificacao']=='Prata' else (
                    'rgba(161,136,127,0.2)' if r['classificacao']=='Bronze' else 'rgba(158,158,158,0.2)'))),
                line=dict(color=cor_class(r['classificacao']), width=2),
                name=nome
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=[100]*len(categorias)+[100],
                theta=categorias+[categorias[0]],
                line=dict(color='#ccc', width=1, dash='dot'),
                name='Meta (100%)', showlegend=False
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,150], ticksuffix="%", tickfont=dict(size=9))),
                showlegend=False, height=320, margin=dict(t=20,b=20,l=20,r=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown("---")

# =============================================
# PÁGINA ER
# =============================================
def pg_er():
    requer_perfil("gerencia")
    st.markdown("## 🏪 ER — Espaço Revendedor")
    st.markdown("---")
    ciclo = get_ciclo_ativo()
    if not ciclo: st.warning("⚠️ Sem ciclo ativo."); return

    ciclos = get_ciclos(); nomes = [c['nome'] for c in ciclos]
    sel = st.selectbox("Ciclo", nomes, index=nomes.index(ciclo['nome']) if ciclo['nome'] in nomes else 0)
    cs = next((c for c in ciclos if c['nome']==sel),ciclo)
    meta_nm = float(get_config('meta_nao_multimarca_caixa',30))
    res = get_resultados_er(cs['id'])
    if not res: st.info("📊 Sem dados ER para este ciclo."); return

    df = pd.DataFrame(res)
    tp = int(df['total_pedidos'].sum())
    tnm = int(df['pedidos_nao_multimarca'].sum())
    pg = tnm/tp*100 if tp>0 else 0

    # Buscar dados brutos do ER do Supabase para análises adicionais
    # Os dados brutos ficam na sessão após o upload — usar df_er_raw se disponível
    df_er_raw = st.session_state.get('df_er_raw', None)

    # KPIs — substituir "caixas acima da meta" por revendedores únicos
    rev_unicos = int(df_er_raw['Pessoa'].nunique()) if df_er_raw is not None else None
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_grande("Total Pedidos", f"{tp:,}".replace(",","."))
    with c2: kpi_grande("Não Multimarca", f"{tnm:,}".replace(",","."))
    with c3: kpi_grande("% Não Multimarca Geral", fmt_pct(pg), cor="#F44336" if pg>meta_nm else "#4CAF50")
    with c4:
        if rev_unicos is not None:
            kpi_grande("Revendedores Únicos", f"{rev_unicos:,}".replace(",","."), "visitaram o ER no ciclo")
        else:
            kpi_grande("Revendedores Únicos", "—", "Reprocesse os dados para ver")

    st.markdown("---")
    st.markdown("### 🏆 Ranking Multimarca")

    df['pedidos_multimarca'] = df['total_pedidos'] - df['pedidos_nao_multimarca']
    df['pct_multimarca'] = 100 - df['pct_nao_multimarca']
    df_rank = df.sort_values('pedidos_multimarca', ascending=False).reset_index(drop=True)

    for pos, row in df_rank.iterrows():
        pos_num = pos + 1
        pm = row['pedidos_multimarca']
        pct_m = row['pct_multimarca']
        cor = "#4CAF50" if pct_m >= 70 else ("#FFC107" if pct_m >= 50 else "#F44336")
        ic = "🟢" if pct_m >= 70 else ("🟡" if pct_m >= 50 else "🔴")
        pos_cores = ["#F9A825","#9E9E9E","#A1887F"]
        pb = pos_cores[pos_num-1] if pos_num<=3 else "#f0f0f0"
        pt = "white" if pos_num<=3 else "#555"
        html = (
            f'<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;'
            f'background:white;border-radius:8px;border:1px solid #eee;margin-bottom:6px">'
            f'<div style="min-width:28px;height:28px;border-radius:50%;background:{pb};'
            f'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:{pt}">{pos_num}</div>'
            f'<div style="flex:1">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="font-weight:600;font-size:14px">{row["usuario_finalizacao"]}</span>'
            f'<div style="display:flex;align-items:center;gap:12px">'
            f'<span style="font-size:12px;color:#999">{int(pm)} multimarca de {int(row["total_pedidos"])} pedidos</span>'
            f'<span style="font-size:16px;font-weight:700;color:{cor}">{ic} {fmt_pct(pct_m)}</span>'
            f'</div></div></div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("---")

    # Análises adicionais — apenas se dados brutos disponíveis
    if df_er_raw is not None:
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("**📍 Revendedores por Bairro**")
            total_rev = df_er_raw['Pessoa'].nunique()
            bairro_rev = df_er_raw.groupby('Bairro')['Pessoa'].nunique().reset_index()
            bairro_rev.columns = ['Bairro','Revendedores']
            bairro_rev['%'] = (bairro_rev['Revendedores'] / total_rev * 100).round(1)
            bairro_rev = bairro_rev.sort_values('Revendedores', ascending=False)
            for _, row in bairro_rev.iterrows():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                    f'border-bottom:1px solid #f0f0f0;font-size:13px">'
                    f'<span style="color:#555">{row["Bairro"]}</span>'
                    f'<span style="font-weight:600">{row["%"]:.1f}%</span>'
                    f'</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown("**🏅 Revendedores por Segmentação**")
            seg_rev = df_er_raw.groupby('Papel')['Pessoa'].nunique().reset_index()
            seg_rev.columns = ['Segmentação','Revendedores']
            seg_rev['%'] = (seg_rev['Revendedores'] / total_rev * 100).round(1)
            seg_rev = seg_rev.sort_values('Revendedores', ascending=False)
            for _, row in seg_rev.iterrows():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                    f'border-bottom:1px solid #f0f0f0;font-size:13px">'
                    f'<span style="color:#555">{row["Segmentação"]}</span>'
                    f'<span style="font-weight:600">{row["%"]:.1f}%</span>'
                    f'</div>', unsafe_allow_html=True)

        with col_c:
            st.markdown("**💳 Forma de Pagamento**")
            total_ped = len(df_er_raw)
            pag_cnt = df_er_raw['PlanoPagamento'].value_counts().reset_index()
            pag_cnt.columns = ['Forma','Pedidos']
            pag_cnt['%'] = (pag_cnt['Pedidos'] / total_ped * 100).round(1)
            for _, row in pag_cnt.iterrows():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                    f'border-bottom:1px solid #f0f0f0;font-size:13px">'
                    f'<span style="color:#555">{row["Forma"]}</span>'
                    f'<span style="font-weight:600">{row["%"]:.1f}%</span>'
                    f'</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Gráfico frequência por dia
        st.markdown("### 📅 Frequência de Revendedores por Dia")
        dias_pt = {0:'Segunda',1:'Terça',2:'Quarta',3:'Quinta',4:'Sexta',5:'Sábado',6:'Domingo'}
        df_er_raw['Data Captação'] = pd.to_datetime(df_er_raw['Data Captação'], dayfirst=True, errors='coerce')
        freq_dia = df_er_raw.groupby('Data Captação')['Pessoa'].nunique().reset_index()
        freq_dia.columns = ['Data','Revendedores']
        freq_dia = freq_dia.dropna(subset=['Data']).sort_values('Data')
        freq_dia['DiaNome'] = freq_dia['Data'].dt.dayofweek.map(dias_pt)
        freq_dia['Label'] = freq_dia['Data'].dt.strftime('%d/%m') + ' (' + freq_dia['DiaNome'] + ')'
        fig3 = go.Figure(go.Bar(
            x=freq_dia['Label'], y=freq_dia['Revendedores'],
            marker_color='#1565C0',
            text=freq_dia['Revendedores'], textposition='outside'
        ))
        fig3.update_layout(height=380, margin=dict(t=20,b=60),
                          xaxis_tickangle=-45, yaxis_title="Revendedores Únicos")
        st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info("ℹ️ Para ver análises de bairro, segmentação, pagamento e frequência, reprocesse os dados em Configurações → Upload.")

    st.markdown("---")
    st.markdown("### 📊 Comparativo por Caixa")
    df_graf = df_rank.sort_values('pedidos_multimarca', ascending=False)
    cores = ["#4CAF50" if p>=70 else ("#FFC107" if p>=50 else "#F44336") for p in df_graf['pct_multimarca']]
    fig = go.Figure(go.Bar(x=df_graf['usuario_finalizacao'],y=df_graf['pct_multimarca'],
        marker_color=cores,text=[fmt_pct(p) for p in df_graf['pct_multimarca']],textposition='outside'))
    fig.update_layout(height=360,margin=dict(t=10,b=10)); fig.update_yaxes(ticksuffix="%",title="% Multimarca")
    st.plotly_chart(fig,use_container_width=True)

    evol=[]
    for c in ciclos[-6:]:
        for r in get_resultados_er(c['id']):
            evol.append({'Ciclo':c['nome'],'Caixa':r['usuario_finalizacao'],'% Multimarca':100-r['pct_nao_multimarca']})
    if evol:
        st.markdown("### 📈 Evolução por Ciclo")
        fig2=px.line(pd.DataFrame(evol),x='Ciclo',y='% Multimarca',color='Caixa',markers=True)
        fig2.update_layout(height=300,margin=dict(t=10,b=10)); fig2.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig2,use_container_width=True)

# =============================================
# PÁGINA CONFIGURAÇÕES
# =============================================
def pg_config():
    requer_perfil("gerencia")
    st.markdown("## ⚙️ Configurações")
    aba = st.radio("", ["Setores","Pontuação & IAF","Ciclos & Metas","Upload","Senhas","Logs"], horizontal=True)
    st.markdown("---")
    sb = get_supabase()
    usuario = st.session_state.get('usuario','sistema')

    if aba == "Setores":
        st.markdown("### Setores")
        st.caption("Setores detectados automaticamente no upload. Defina o tipo e status de cada um.")
        setores_db = sb.table("setores").select("*").order("nome").execute().data or []
        if not setores_db:
            st.info("Nenhum setor encontrado. Faça o upload das planilhas primeiro.")
        else:
            for s in setores_db:
                c1,c2,c3,c4 = st.columns([3,2,2,1])
                c1.markdown(f"**{s['nome']}**")
                with c2: ti = st.selectbox("Tipo",["financeiro","base"],index=0 if s['tipo']=='financeiro' else 1,key=f"t{s['id']}")
                with c3: at = st.selectbox("Status",["Ativo","Inativo"],index=0 if s['ativo'] else 1,key=f"a{s['id']}")
                with c4:
                    if st.button("💾",key=f"s{s['id']}"):
                        sb.table("setores").update({"tipo":ti,"ativo":at=="Ativo"}).eq("id",s['id']).execute()
                        st.success("✓"); st.rerun()

    elif aba == "Pontuação & IAF":
        st.caption("Ajuste os pesos e faixas de classificação. Clique em Salvar ao terminar.")
        t1,t2,t3 = st.tabs(["Pontuação Base","Pontuação Financeiro","Faixas & IAF"])
        with t1:
            c1,c2 = st.columns(2)
            with c1: pts_ir = st.number_input("Inícios+Reinícios (pts)", value=int(get_config('pts_inicios_reinicios',800)), step=50)
            with c2: pts_g = st.number_input("Meta Grupo (pts)", value=int(get_config('pts_meta_grupo',200)), step=50)
        with t2:
            c1,c2 = st.columns(2)
            with c1:
                pts_m = st.number_input("Por Marca (pts)", value=int(get_config('pts_por_marca_receita',100)), step=10)
                pts_mu = st.number_input("Multimarcas (pts)", value=int(get_config('pts_multimarcas',100)), step=10)
                pts_c = st.number_input("Cabelos % (pts)", value=int(get_config('pts_pct_cabelos',100)), step=10)
            with c2:
                pts_mk = st.number_input("Make % (pts)", value=int(get_config('pts_pct_make',100)), step=10)
                pts_a = st.number_input("Atividade (pts)", value=int(get_config('pts_atividade',100)), step=10)
                mc = st.number_input("Meta máx % não multimarca ER", value=float(get_config('meta_nao_multimarca_caixa',30)))
        with t3:
            c1,c2 = st.columns(2)
            with c1:
                st.caption("% da meta para pontuação parcial")
                f50 = st.number_input("≥X% → 50% dos pts", value=int(get_config('faixa_pontuacao_50pct',85)))
                f75 = st.number_input("≥X% → 75% dos pts", value=int(get_config('faixa_pontuacao_75pct',95)))
                f100 = st.number_input("≥X% → 100% dos pts", value=int(get_config('faixa_pontuacao_100pct',100)))
            with c2:
                st.caption("IAF mínimo por classificação (%)")
                br = st.number_input("Bronze ≥", value=int(get_config('faixa_bronze_min',65)))
                pr = st.number_input("Prata ≥", value=int(get_config('faixa_prata_min',75)))
                ou = st.number_input("Ouro ≥", value=int(get_config('faixa_ouro_min',85)))
                di = st.number_input("Diamante ≥", value=int(get_config('faixa_diamante_min',95)))
        if st.button("💾 Salvar configurações", use_container_width=True):
            for k,v in [('pts_inicios_reinicios',pts_ir),('pts_meta_grupo',pts_g),('pts_por_marca_receita',pts_m),
                        ('pts_multimarcas',pts_mu),('pts_pct_cabelos',pts_c),('pts_pct_make',pts_mk),('pts_atividade',pts_a),
                        ('faixa_pontuacao_50pct',f50),('faixa_pontuacao_75pct',f75),('faixa_pontuacao_100pct',f100),
                        ('faixa_bronze_min',br),('faixa_prata_min',pr),('faixa_ouro_min',ou),('faixa_diamante_min',di),
                        ('meta_nao_multimarca_caixa',mc)]:
                set_config(k,str(v),usuario)
            st.success("✅ Salvo!")

    elif aba == "Ciclos & Metas":
        tc,tm = st.tabs(["Ciclos","Metas do Período"])
        with tc:
            with st.expander("➕ Novo ciclo"):
                nc = st.text_input("Nome (ex: 05/2026)")
                d1,d2 = st.columns(2)
                di = d1.date_input("Início"); df_c = d2.date_input("Fim")
                if st.button("Criar"):
                    if nc:
                        sb.table("ciclos").insert({"nome":nc,"data_inicio":str(di),"data_fim":str(df_c),"ativo":True}).execute()
                        st.success("Criado!"); st.rerun()
            for c in get_ciclos():
                cc1,cc2,cc3 = st.columns([3,2,2])
                cc1.markdown(f"**{c['nome']}**")
                cc2.markdown("✅ Ativo" if c['ativo'] else "⬜ Inativo")
                if not c['ativo']:
                    with cc3:
                        if st.button("Ativar",key=f"at{c['id']}"):
                            sb.table("ciclos").update({"ativo":False}).execute()
                            sb.table("ciclos").update({"ativo":True}).eq("id",c['id']).execute(); st.rerun()
        with tm:
            ca = get_ciclo_ativo()
            if not ca: st.warning("Crie e ative um ciclo primeiro."); st.stop()
            st.caption(f"Ciclo ativo: **{ca['nome']}**")
            setores = get_setores()
            mex = {m['setor_id']:m for m in get_metas(ca['id'])}
            tb,tf = st.tabs(["Base","Financeiro"])
            with tb:
                for s in [x for x in setores if x['tipo']=='base']:
                    ma = mex.get(s['id'],{})
                    with st.expander(s['nome'], expanded=False):
                        b1,b2 = st.columns(2)
                        mir = b1.number_input("Meta I+R",min_value=0,value=int(ma.get('meta_inicios_reinicios',0)),key=f"mir{s['id']}")
                        rir = b2.number_input("Realizado I+R",min_value=0,value=int(ma.get('realizado_inicios_reinicios',0)),key=f"rir{s['id']}")
                        if st.button("💾 Salvar",key=f"sb{s['id']}"):
                            upsert_meta(ca['id'],s['id'],{'meta_inicios_reinicios':mir,'realizado_inicios_reinicios':rir,'updated_by':usuario})
                            st.success("Salvo!")
            with tf:
                for s in [x for x in setores if x['tipo']=='financeiro']:
                    ma = mex.get(s['id'],{})
                    with st.expander(s['nome'], expanded=False):
                        f1,f2,f3 = st.columns(3)
                        with f1:
                            st.caption("Receitas R$")
                            mbo = st.number_input("Boticário",min_value=0.0,value=float(ma.get('meta_boticario',0)),key=f"mb{s['id']}")
                            meu = st.number_input("Eudora",min_value=0.0,value=float(ma.get('meta_eudora',0)),key=f"me{s['id']}")
                            mou = st.number_input("OUI",min_value=0.0,value=float(ma.get('meta_oui',0)),key=f"mo{s['id']}")
                            mqd = st.number_input("QDB",min_value=0.0,value=float(ma.get('meta_qdb',0)),key=f"mq{s['id']}")
                            mca = st.number_input("Cabelos R$",min_value=0.0,value=float(ma.get('meta_cabelos',0)),key=f"mc{s['id']}")
                            mma = st.number_input("Make R$",min_value=0.0,value=float(ma.get('meta_make',0)),key=f"mm{s['id']}")
                        with f2:
                            st.caption("Indicadores %")
                            mmu = st.number_input("Multimarcas%",0.0,100.0,float(ma.get('meta_multimarcas',0)),key=f"mmu{s['id']}")
                            mpc = st.number_input("Cabelos%",0.0,100.0,float(ma.get('meta_pct_cabelos',0)),key=f"mpc{s['id']}")
                            mpm = st.number_input("Make%",0.0,100.0,float(ma.get('meta_pct_make',0)),key=f"mpm{s['id']}")
                            mat = st.number_input("Atividade%",0.0,100.0,float(ma.get('meta_atividade',0)),key=f"mat{s['id']}")
                        with f3:
                            st.caption("Base")
                            mtb = st.number_input("Tamanho Base",0,value=int(ma.get('tamanho_base',0)),key=f"mtb{s['id']}")
                        if st.button("💾 Salvar",key=f"sf{s['id']}"):
                            upsert_meta(ca['id'],s['id'],{'meta_boticario':mbo,'meta_eudora':meu,'meta_oui':mou,'meta_qdb':mqd,
                                'meta_cabelos':mca,'meta_make':mma,'meta_multimarcas':mmu,'meta_pct_cabelos':mpc,
                                'meta_pct_make':mpm,'meta_atividade':mat,'tamanho_base':mtb,'updated_by':usuario})
                            st.success("Salvo!")

    elif aba == "Upload":
        requer_perfil("admin")
        st.markdown("### Upload de Planilhas")
        ca = get_ciclo_ativo()
        if not ca: st.warning("Sem ciclo ativo."); return
        st.info(f"Ciclo: **{ca['nome']}**")
        uploaded = {}; c1u,c2u = st.columns(2)
        for i,nm in enumerate(ARQS):
            with (c1u if i%2==0 else c2u):
                f = st.file_uploader(f"📁 {nm}.xlsx",type=['xlsx'],key=f"up{nm}")
                if f: uploaded[nm] = f
        if uploaded and st.button("🚀 Processar",use_container_width=True,type="primary"):
            with st.spinner("Processando..."):
                try:
                    dfs = {}
                    for nm,arq in uploaded.items():
                        dfs[nm] = pd.read_excel(arq) if nm in ['ER','Ativos'] else ler_planilha(arq,nm)
                    # Sincronizar setores automaticamente
                    setores_encontrados = set()
                    for nm in ['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos']:
                        if nm in dfs and 'Setor' in dfs[nm].columns:
                            for s in dfs[nm]['Setor'].dropna().unique():
                                setores_encontrados.add(str(s).strip())
                    setores_existentes = {s['nome'] for s in (sb.table("setores").select("nome").execute().data or [])}
                    novos = setores_encontrados - setores_existentes
                    for s in novos:
                        sb.table("setores").insert({"nome":s,"tipo":"financeiro","ativo":True}).execute()
                    if novos:
                        st.info(f"ℹ️ {len(novos)} novos setores detectados. Classifique-os em Configurações → Setores.")
                    cfg = {r['chave']:r['valor'] for r in (sb.table("configuracoes").select("chave,valor").execute().data or [])}
                    res_p = processar_ciclo(dfs,get_metas(ca['id']),get_setores(),cfg)
                    for r in res_p['resultados']:
                        r['ciclo_id'] = ca['id']
                        sb.table("resultados").upsert(r,on_conflict="ciclo_id,setor_id").execute()
                    for r in res_p['resultados_er']:
                        r['ciclo_id'] = ca['id']
                        sb.table("resultados_er").upsert(r,on_conflict="ciclo_id,usuario_finalizacao").execute()
                    for nm in uploaded: log_upload(ca['id'],nm,usuario)
                    # Salvar ER bruto na sessão para análises da página ER
                    if 'ER' in dfs:
                        st.session_state['df_er_raw'] = dfs['ER']
                    st.success(f"✅ {len(uploaded)} arquivo(s) processados com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    elif aba == "Senhas":
        requer_perfil("admin")
        st.markdown("### Senhas de Acesso")
        st.warning("⚠️ Alterar senhas afeta todos os usuários.")
        s1,s2,s3 = st.columns(3)
        with s1:
            st.caption("Perfil Leitura")
            nl = st.text_input("Nova senha",type="password",key="nl")
            if st.button("Alterar",key="al"):
                if nl: set_config('senha_leitura',nl,usuario); st.success("✓")
        with s2:
            st.caption("Perfil Gerência")
            ng = st.text_input("Nova senha",type="password",key="ng")
            if st.button("Alterar",key="ag"):
                if ng: set_config('senha_gerencia',ng,usuario); st.success("✓")
        with s3:
            st.caption("Perfil Admin")
            na = st.text_input("Nova senha",type="password",key="na")
            if st.button("Alterar",key="aa"):
                if na: set_config('senha_admin',na,usuario); st.success("✓")

    elif aba == "Logs":
        st.markdown("### Logs do Sistema")
        tl1,tl2 = st.tabs(["Uploads","Alterações"])
        with tl1:
            ca = get_ciclo_ativo()
            if ca:
                logs = get_logs_upload(ca['id'])
                if logs:
                    dl = pd.DataFrame(logs)
                    dl['data_upload'] = pd.to_datetime(dl['data_upload']).dt.strftime('%d/%m/%Y %H:%M')
                    st.dataframe(dl[['arquivo','usuario','data_upload']],use_container_width=True)
                else:
                    st.info("Sem uploads registrados.")
        with tl2:
            r = sb.table("log_alteracoes").select("*").order("created_at",desc=True).limit(50).execute()
            if r.data:
                dla = pd.DataFrame(r.data)
                dla['created_at'] = pd.to_datetime(dla['created_at']).dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(dla[['tabela','campo','valor_anterior','valor_novo','usuario','created_at']],use_container_width=True)
            else:
                st.info("Sem alterações registradas.")

# =============================================
# MAIN
# =============================================
check_auth()
if not st.session_state.get("perfil"):
    login_screen()
else:
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.usuario}**")
        st.markdown(f"🔑 `{st.session_state.perfil}`")
        st.markdown("---")
        pg = st.radio("", ["🏠 Home","👥 Base","💼 Financeiro","🏪 ER","⚙️ Configurações"])
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.perfil = None; st.session_state.usuario = None; st.rerun()
    if pg == "🏠 Home": pg_home()
    elif pg == "👥 Base": pg_base()
    elif pg == "💼 Financeiro": pg_financeiro()
    elif pg == "🏪 ER": pg_er()
    elif pg == "⚙️ Configurações": pg_config()
