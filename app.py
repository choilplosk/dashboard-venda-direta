import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Dashboard Venda Direta", page_icon="💼", layout="wide")

# =============================================
# TEMA VISUAL
# =============================================
st.markdown("""<style>
    .block-container { padding-top: 0.5rem; padding-left: 1.2rem; padding-right: 1.2rem; }
    .stApp { background: #f0f2f5; }
    section[data-testid="stSidebar"] { background: #1a2e4a !important; }
    section[data-testid="stSidebar"] > div { background: #1a2e4a !important; }
    section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] .stRadio label { font-size: 13px !important; padding: 6px 0; }
    section[data-testid="stSidebar"] .stRadio label:hover { color: white !important; }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: white !important; }
    section[data-testid="stSidebar"] .stSelectbox label { color: #94a3b8 !important; font-size: 11px !important; }
    section[data-testid="stSidebar"] .stSelectbox div { background: #2d4a6e !important; border: none !important; color: white !important; }
    section[data-testid="stSidebar"] .stButton button { background: transparent !important; border: 1px solid #2d4a6e !important; color: #94a3b8 !important; font-size: 12px; }
    section[data-testid="stSidebar"] .stButton button:hover { color: white !important; border-color: #94a3b8 !important; }
    div[data-testid="metric-container"] { background: white; border-radius:10px; padding:12px; }
    .stTabs [data-baseweb="tab"] { font-size: 12px; }
    .stTabs [data-baseweb="tab-list"] { background: white; border-radius: 8px; padding: 2px; gap: 2px; }
    .stTabs [aria-selected="true"] { background: #1a2e4a !important; color: white !important; border-radius: 6px; }
    .stSelectbox label { font-size: 12px; color: #64748b; }
    .stExpander { background: white; border: 0.5px solid #e2e8f0 !important; border-radius: 8px !important; }
    h1,h2,h3,h4 { color: #1a2e4a !important; font-weight: 700 !important; }
    .stMarkdown hr { margin: 0.4rem 0; border-color: #e2e8f0; }
    .stAlert { border-radius: 8px !important; }
    p { font-size: 13px; }
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

def fmt_br(valor, dec=2):
    return f"{valor:_.{dec}f}".replace("_","X").replace(".",",").replace("X",".")

def fmt_moeda(v): return f"R$ {fmt_br(v)}"
def fmt_pct(v, dec=1): return f"{v:.{dec}f}%".replace(".",",")
def fmt_int(v): return f"{int(v):,}".replace(",",".")

PERFIS = {"leitura":1,"gerencia":2,"admin":3}

def check_auth():
    if "perfil" not in st.session_state: st.session_state.perfil = None
    if "usuario" not in st.session_state: st.session_state.usuario = None
    if "ciclo_sel_id" not in st.session_state: st.session_state.ciclo_sel_id = None

def login_screen():
    _, col, _ = st.columns([1,1,1])
    with col:
        st.markdown(
            '<div style="background:#1a2e4a;border-radius:12px;padding:28px 24px;margin:40px 0 20px;text-align:center">'
            '<div style="font-size:20px;font-weight:700;color:white;margin-bottom:4px">💼 Venda Direta</div>'
            '<div style="font-size:12px;color:#94a3b8">Dashboard de Gestão</div>'
            '</div>', unsafe_allow_html=True)
        nome = st.text_input("Nome")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True, type="primary"):
            if not nome: st.error("Informe seu nome.")
            elif senha == get_config("senha_admin","admin123"):
                st.session_state.perfil="admin"; st.session_state.usuario=nome; st.rerun()
            elif senha == get_config("senha_gerencia","gerencia123"):
                st.session_state.perfil="gerencia"; st.session_state.usuario=nome; st.rerun()
            elif senha == get_config("senha_leitura","leitura123"):
                st.session_state.perfil="leitura"; st.session_state.usuario=nome; st.rerun()
            else: st.error("Senha incorreta.")

def requer_perfil(p):
    if PERFIS.get(st.session_state.get("perfil"),0) < PERFIS.get(p,99):
        st.warning("⛔ Sem permissão."); st.stop()

def cor_class(c):
    return {'Diamante':'#1a2e4a','Ouro':'#F9A825','Prata':'#64748b','Bronze':'#92400e'}.get(c,'#94a3b8')

def emoji_class(c):
    return {'Diamante':'💎','Ouro':'🥇','Prata':'🥈','Bronze':'🥉'}.get(c,'—')

def class_iaf(iaf, cfg={}):
    if iaf >= float(cfg.get('faixa_diamante_min',95)): return 'Diamante'
    if iaf >= float(cfg.get('faixa_ouro_min',85)): return 'Ouro'
    if iaf >= float(cfg.get('faixa_prata_min',75)): return 'Prata'
    if iaf >= float(cfg.get('faixa_bronze_min',65)): return 'Bronze'
    return 'Não Classificado'

def calc_pts(realizado, meta, pts_max, f50, f75, f100):
    if meta <= 0: return 0.0
    p = realizado/meta*100
    if p >= f100: return pts_max
    if p >= f75: return pts_max*0.75
    if p >= f50: return pts_max*0.50
    return 0.0

def ler_planilha(arquivo, marca):
    df = pd.read_excel(arquivo); df['Marca'] = marca
    return df[~df['ValorPraticado'].isin([0,6])] if marca=='Oui' else df[df['ValorPraticado']>0]

def calc_multimarcas(df_ativos, dfs):
    at = df_ativos[df_ativos['ValorPraticado']>0].copy()
    cods = set(at['CodigoRevendedora'].unique())
    cnt = {c:0 for c in cods}
    for m in ['Boticario','Eudora','Oui','QDB']:
        if m in dfs:
            cm = set(dfs[m]['CodigoRevendedora'].unique())
            for c in cods:
                if c in cm: cnt[c]+=1
    multi = {c for c,n in cnt.items() if n>=2}
    at['is_multimarca'] = at['CodigoRevendedora'].isin(multi)
    return at

def processar_ciclo(dfs, metas_list, setores_list, cfg):
    df_ativos = dfs.get('Ativos')
    f50=float(cfg.get('faixa_pontuacao_50pct',85)); f75=float(cfg.get('faixa_pontuacao_75pct',95)); f100=float(cfg.get('faixa_pontuacao_100pct',100))
    pts_ir=float(cfg.get('pts_inicios_reinicios',800)); pts_g=float(cfg.get('pts_meta_grupo',200))
    pts_m=float(cfg.get('pts_por_marca_receita',100)); pts_mu=float(cfg.get('pts_multimarcas',100))
    pts_cab=float(cfg.get('pts_pct_cabelos',100)); pts_mak=float(cfg.get('pts_pct_make',100)); pts_at=float(cfg.get('pts_atividade',100))
    md = {m['setor_id']:m for m in metas_list}
    df_multi = calc_multimarcas(df_ativos, dfs) if df_ativos is not None else None
    resultados = []
    for s in setores_list:
        sid,nome,tipo = s['id'],s['nome'],s['tipo']
        meta = md.get(sid,{})
        if tipo=='base':
            real=int(meta.get('realizado_inicios_reinicios',0)); m_ir=int(meta.get('meta_inicios_reinicios',0))
            pts=calc_pts(real,m_ir,pts_ir,f50,f75,f100)
            resultados.append({'setor_id':sid,'tipo':'base','valor_boticario':0,'valor_eudora':0,
                'valor_oui':0,'valor_qdb':0,'valor_cabelos':0,'valor_make':0,
                'pct_multimarcas':0,'pct_cabelos':0,'pct_make':0,'pct_atividade':0,
                'ativos':0,'inicios_reinicios':real,'pontuacao_obtida':pts,'pontuacao_maxima':pts_ir,'iaf':0.0,'classificacao':'Não Classificado'})
        else:
            vals,po,pm = {},0.0,0.0
            for marca,cv,cm_key in [('Boticario','valor_boticario','meta_boticario'),('Eudora','valor_eudora','meta_eudora'),
                                     ('Oui','valor_oui','meta_oui'),('QDB','valor_qdb','meta_qdb'),
                                     ('Cabelos','valor_cabelos','meta_cabelos'),('Make','valor_make','meta_make')]:
                df=dfs.get(marca); val=df[df['Setor']==nome]['ValorPraticado'].sum() if df is not None else 0.0
                vals[cv]=val; mv=float(meta.get(cm_key,0))
                if mv>0: po+=calc_pts(val,mv,pts_m,f50,f75,f100); pm+=pts_m
            at_s=None; n_at=0
            if df_ativos is not None:
                at_s=df_ativos[(df_ativos['Setor']==nome)&(df_ativos['ValorPraticado']>0)]
                n_at=at_s['CodigoRevendedora'].nunique()
            pct_mu=0.0
            if df_multi is not None and n_at>0:
                pct_mu=df_multi[(df_multi['Setor']==nome)&(df_multi['is_multimarca'])]['CodigoRevendedora'].nunique()/n_at*100
            m_mu=float(meta.get('meta_multimarcas',0))
            if m_mu>0: po+=calc_pts(pct_mu,m_mu,pts_mu,f50,f75,f100); pm+=pts_mu
            pct_cab_v=0.0
            if dfs.get('Cabelos') is not None and n_at>0 and at_s is not None:
                pct_cab_v=len(set(at_s['CodigoRevendedora'].unique())&set(dfs['Cabelos'][dfs['Cabelos']['Setor']==nome]['CodigoRevendedora'].unique()))/n_at*100
            m_cab=float(meta.get('meta_pct_cabelos',0))
            if m_cab>0: po+=calc_pts(pct_cab_v,m_cab,pts_cab,f50,f75,f100); pm+=pts_cab
            pct_mak_v=0.0
            if dfs.get('Make') is not None and n_at>0 and at_s is not None:
                pct_mak_v=len(set(at_s['CodigoRevendedora'].unique())&set(dfs['Make'][dfs['Make']['Setor']==nome]['CodigoRevendedora'].unique()))/n_at*100
            m_mak=float(meta.get('meta_pct_make',0))
            if m_mak>0: po+=calc_pts(pct_mak_v,m_mak,pts_mak,f50,f75,f100); pm+=pts_mak
            tb=int(meta.get('tamanho_base',0)); pct_at_v=n_at/tb*100 if tb>0 else 0.0
            m_at=float(meta.get('meta_atividade',0))
            if m_at>0: po+=calc_pts(pct_at_v,m_at,pts_at,f50,f75,f100); pm+=pts_at
            iaf=po/pm*100 if pm>0 else 0.0
            resultados.append({'setor_id':sid,'tipo':'financeiro',**vals,
                'pct_multimarcas':round(pct_mu,2),'pct_cabelos':round(pct_cab_v,2),'pct_make':round(pct_mak_v,2),
                'pct_atividade':round(pct_at_v,2),'ativos':n_at,'inicios_reinicios':0,
                'pontuacao_obtida':round(po,2),'pontuacao_maxima':round(pm,2),'iaf':round(iaf,2),'classificacao':class_iaf(iaf,cfg)})
    base_res=[r for r in resultados if r['tipo']=='base']
    t_real=sum(r['inicios_reinicios'] for r in base_res)
    t_meta=sum(int(md.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in setores_list if s['tipo']=='base')
    gb=t_meta>0 and t_real>=t_meta
    for r in base_res:
        r['pontuacao_obtida']+=pts_g if gb else 0; r['pontuacao_maxima']+=pts_g
        r['iaf']=round(r['pontuacao_obtida']/r['pontuacao_maxima']*100 if r['pontuacao_maxima']>0 else 0,2)
        r['classificacao']=class_iaf(r['iaf'],cfg)
    er_res=[]
    if df_ativos is not None and dfs.get('ER') is not None and df_multi is not None:
        nao_m=set(df_multi[~df_multi['is_multimarca']]['CodigoRevendedora'].unique())
        df_er=dfs['ER'].copy(); df_er['is_nm']=df_er['Pessoa'].isin(nao_m)
        for u,g in df_er.groupby('Usuario de Finalização'):
            tot=len(g); nm=int(g['is_nm'].sum())
            er_res.append({'usuario_finalizacao':u,'total_pedidos':tot,'pedidos_nao_multimarca':nm,
                           'pct_nao_multimarca':round(nm/tot*100 if tot>0 else 0,2)})
        er_res.sort(key=lambda x:x['pct_nao_multimarca'],reverse=True)
    ativos_unicos_global=int(df_ativos[df_ativos['ValorPraticado']>0]['CodigoRevendedora'].nunique()) if df_ativos is not None else 0
    return {'resultados':resultados,'resultados_er':er_res,'t_real':t_real,'t_meta':t_meta,'ativos_unicos_global':ativos_unicos_global}

# =============================================
# COMPONENTES VISUAIS
# =============================================
def card_kpi(label, valor, subtexto=None, cor="#1a2e4a", delta=None):
    delta_html = ""
    if delta is not None:
        dc = "#16a34a" if delta>=0 else "#dc2626"
        ds = ("▲ " if delta>=0 else "▼ ") + f"{abs(delta):.1f}%"
        delta_html = f'<div style="font-size:11px;color:{dc};font-weight:600;margin-top:3px">{ds}</div>'
    sub_html = f'<div style="font-size:11px;color:#94a3b8;margin-top:3px">{subtexto}</div>' if subtexto else ""
    html = (
        f'<div style="background:white;border-radius:10px;padding:14px 16px;'
        f'border-top:3px solid {cor};margin-bottom:2px">'
        f'<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px">{label}</div>'
        f'<div style="font-size:26px;font-weight:700;color:{cor};line-height:1">{valor}</div>'
        f'{sub_html}{delta_html}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def semaforo_linha(pct, label, realizado_str, meta_str):
    cor="#94a3b8" if pct==0 else ("#16a34a" if pct>=100 else ("#d97706" if pct>=95 else "#dc2626"))
    ic="⚪" if pct==0 else ("🟢" if pct>=100 else ("🟡" if pct>=95 else "🔴"))
    return (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:6px 0;border-bottom:1px solid #f1f5f9">'
        f'<span style="font-size:12px;color:#475569">{ic} {label}</span>'
        f'<div style="text-align:right">'
        f'<span style="font-size:13px;font-weight:600;color:{cor}">{realizado_str}</span>'
        f'<span style="font-size:11px;color:#94a3b8"> / {meta_str}</span>'
        f'<br><span style="font-size:11px;color:{cor};font-weight:600">{pct:.0f}%</span>'
        f'</div></div>'
    )

def linha_rank(pos, nome, iaf, cl, delta=None, extra=None, atencao=False):
    cor=cor_class(cl); em=emoji_class(cl)
    pos_bg=["#F9A825","#94a3b8","#92400e"][pos-1] if pos<=3 else "#e2e8f0"
    pos_txt="white" if pos<=3 else "#475569"
    barra=min(iaf,100)
    html=(
        f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;'
        f'background:white;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:4px;'
        f'{"border-left:3px solid #dc2626;" if atencao else ""}">'
        f'<div style="min-width:26px;height:26px;border-radius:50%;background:{pos_bg};'
        f'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:{pos_txt}">{pos}</div>'
        f'<div style="flex:1">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
        f'<span style="font-weight:600;font-size:13px;color:#1e293b">{nome}</span>'
        f'<div style="display:flex;align-items:center;gap:8px">'
    )
    if atencao:
        html += '<span style="font-size:10px;background:#fee2e2;color:#dc2626;padding:1px 6px;border-radius:4px">atenção</span>'
    if delta is not None:
        dc="#16a34a" if delta>=0 else "#dc2626"
        ds=("▲" if delta>=0 else "▼")+f"{abs(delta):.1f}%"
        html += f'<span style="font-size:11px;color:{dc}">{ds}</span>'
    html += (
        f'<span style="font-weight:700;font-size:15px;color:{cor}">{iaf:.1f}%</span>'
        f'<span style="background:{cor};color:white;padding:1px 8px;border-radius:10px;font-size:11px">{em} {cl}</span>'
    )
    if extra:
        html += f'<span style="font-size:11px;color:#94a3b8">{extra}</span>'
    html += (
        f'</div></div>'
        f'<div style="background:#f1f5f9;border-radius:3px;height:4px;overflow:hidden">'
        f'<div style="background:{cor};width:{barra:.1f}%;height:100%;border-radius:3px"></div>'
        f'</div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def tabela_mini(titulo, dados, col_label, col_pct, col_extra=None):
    st.markdown(f'<p style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">{titulo}</p>', unsafe_allow_html=True)
    html='<div style="background:white;border-radius:8px;border:1px solid #e2e8f0;overflow:hidden">'
    for i,(_,row) in enumerate(dados.iterrows()):
        bg="#f8fafc" if i%2==0 else "white"
        extra_html=f'<span style="font-size:11px;color:#94a3b8;margin-left:8px">{row[col_extra]}</span>' if col_extra and col_extra in row else ""
        html+=(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:5px 10px;background:{bg}">'
            f'<span style="font-size:12px;color:#475569">{row[col_label]}</span>'
            f'<div>'
            f'<span style="font-size:12px;font-weight:600;color:#1e293b">{row[col_pct]:.1f}%</span>'
            f'{extra_html}</div></div>'
        )
    html+='</div>'
    st.markdown(html, unsafe_allow_html=True)

ARQS=['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos','ER']
MARCAS_CFG=[('valor_boticario','meta_boticario','Boticário'),('valor_eudora','meta_eudora','Eudora'),
            ('valor_oui','meta_oui','OUI'),('valor_qdb','meta_qdb','QDB'),
            ('valor_cabelos','meta_cabelos','Cabelos'),('valor_make','meta_make','Make')]
INDS_PCT=[('pct_multimarcas','meta_multimarcas','Multimarcas'),('pct_cabelos','meta_pct_cabelos','Cabelos %'),
          ('pct_make','meta_pct_make','Make %'),('pct_atividade','meta_atividade','Atividade')]

# =============================================
# PÁGINA HOME
# =============================================
def pg_home(ciclo_id):
    ciclo=get_ciclo_ativo()
    ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==ciclo_id),ciclo) if ciclo_id else ciclo
    if not cs:
        st.warning("⚠️ Nenhum ciclo ativo."); return
    st.markdown(f"### Visão Geral — {cs['nome']}")
    st.markdown("---")
    res=get_resultados(cs['id'])
    if not res: st.info("📊 Aguardando processamento."); _status_arquivos(cs); return
    df=pd.DataFrame(res)
    fin=df[df['tipo']=='financeiro']; base=df[df['tipo']=='base']
    mc=['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make']
    receita_total=df[mc].sum().sum()
    # Ativos únicos globais
    chave_ativos=f"ativos_unicos_{cs['id']}"
    total_ativos=int(get_config(chave_ativos,0) or 0)
    # Metas consolidadas
    sf=get_setores(tipo='financeiro')
    ids_fin={s['id'] for s in sf}
    metas_h={m['setor_id']:m for m in get_metas(cs['id'])}
    meta_rec=sum(float(metas_h.get(sid,{}).get(f'meta_{m}',0)) for sid in ids_fin for m in ['boticario','eudora','oui','qdb','cabelos','make'])
    meta_ativ=sum(float(metas_h.get(sid,{}).get('meta_atividade',0)) for sid in ids_fin)/len(sf) if sf else 0
    meta_make=sum(float(metas_h.get(sid,{}).get('meta_pct_make',0)) for sid in ids_fin)/len(sf) if sf else 0
    meta_cab=sum(float(metas_h.get(sid,{}).get('meta_pct_cabelos',0)) for sid in ids_fin)/len(sf) if sf else 0
    total_base=sum(int(metas_h.get(sid,{}).get('tamanho_base',0)) for sid in ids_fin)
    pct_ativ=total_ativos/total_base*100 if total_base>0 else 0
    pct_make=fin['pct_make'].mean() if len(fin)>0 else 0
    pct_cab=fin['pct_cabelos'].mean() if len(fin)>0 else 0
    pct_rec=receita_total/meta_rec*100 if meta_rec>0 else 0
    # Delta vs ciclo anterior
    c_ant=next((c for c in ciclos if c['id']<cs['id']),None)
    delta_rec=delta_ativ=delta_make=delta_cab=None
    if c_ant:
        res_ant=get_resultados(c_ant['id'])
        if res_ant:
            df_ant=pd.DataFrame(res_ant)
            fin_ant=df_ant[df_ant['tipo']=='financeiro']
            rec_ant=df_ant[mc].sum().sum()
            delta_rec=((receita_total-rec_ant)/rec_ant*100) if rec_ant>0 else None
            delta_make=(pct_make-fin_ant['pct_make'].mean()) if len(fin_ant)>0 else None
            delta_cab=(pct_cab-fin_ant['pct_cabelos'].mean()) if len(fin_ant)>0 else None
            ativos_ant=int(get_config(f"ativos_unicos_{c_ant['id']}",0) or 0)
            base_ant=sum(int({m['setor_id']:m for m in get_metas(c_ant['id'])}.get(sid,{}).get('tamanho_base',0)) for sid in ids_fin)
            pct_ativ_ant=ativos_ant/base_ant*100 if base_ant>0 else 0
            delta_ativ=pct_ativ-pct_ativ_ant
    cor_rec="#16a34a" if pct_rec>=100 else ("#d97706" if pct_rec>=95 else "#dc2626")
    cor_ativ="#16a34a" if pct_ativ>=100 else ("#d97706" if pct_ativ>=95 else "#dc2626")
    cor_make="#16a34a" if (pct_make/meta_make*100 if meta_make>0 else 0)>=100 else "#d97706" if (pct_make/meta_make*100 if meta_make>0 else 0)>=95 else "#dc2626"
    cor_cab="#16a34a" if (pct_cab/meta_cab*100 if meta_cab>0 else 0)>=100 else "#d97706" if (pct_cab/meta_cab*100 if meta_cab>0 else 0)>=95 else "#dc2626"
    c1,c2,c3,c4=st.columns(4)
    with c1: card_kpi("Receita Total",fmt_moeda(receita_total),f"meta {fmt_moeda(meta_rec)} ({pct_rec:.0f}%)" if meta_rec>0 else None,cor_rec,delta_rec)
    with c2: card_kpi("Atividade Global",fmt_pct(pct_ativ),f"meta {fmt_pct(meta_ativ)}" if meta_ativ>0 else None,cor_ativ,delta_ativ)
    with c3: card_kpi("Make",fmt_pct(pct_make),f"meta {fmt_pct(meta_make)}" if meta_make>0 else None,cor_make,delta_make)
    with c4: card_kpi("Cabelos",fmt_pct(pct_cab),f"meta {fmt_pct(meta_cab)}" if meta_cab>0 else None,cor_cab,delta_cab)
    st.markdown("")
    # Pódio
    st.markdown("#### 🏆 Pódio do Ciclo")
    try:
        slist=get_supabase().table("setores").select("id,nome,ativo").execute().data or []
        nomes_map={s['id']:s['nome'] for s in slist}
        ids_ativos_h={s['id'] for s in slist if s['ativo']}
    except:
        nomes_map={}; ids_ativos_h=set()
    todos=df[df['setor_id'].isin(ids_ativos_h)].sort_values('iaf',ascending=False).head(3)
    cp=st.columns(3)
    for i,(_,r) in enumerate(todos.iterrows()):
        nm=nomes_map.get(r['setor_id'],"—"); cor=cor_class(r['classificacao'])
        with cp[i]:
            st.markdown(
                f'<div style="background:white;border-radius:10px;padding:16px;text-align:center;'
                f'box-shadow:0 1px 3px rgba(0,0,0,0.08);border-top:3px solid {cor}">'
                f'<div style="font-size:24px">{"🥇🥈🥉"[i]}</div>'
                f'<div style="font-size:13px;font-weight:600;color:#1e293b;margin:6px 0">{nm}</div>'
                f'<div style="font-size:26px;font-weight:700;color:{cor}">{fmt_pct(r["iaf"])}</div>'
                f'<div style="font-size:11px;color:#64748b">{emoji_class(r["classificacao"])} {r["classificacao"]}</div>'
                f'</div>', unsafe_allow_html=True)
    st.markdown("")
    # Tabela classificações
    st.markdown("#### 🏅 Classificações")
    todos_res=df[df['setor_id'].isin(ids_ativos_h)].sort_values('iaf',ascending=False)
    for _,r in todos_res.iterrows():
        nm=nomes_map.get(r['setor_id'],str(r['setor_id'])); cor=cor_class(r['classificacao']); em=emoji_class(r['classificacao'])
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 14px;border-radius:8px;border-left:3px solid {cor};'
            f'background:white;border-top:1px solid #f1f5f9;border-right:1px solid #f1f5f9;'
            f'border-bottom:1px solid #f1f5f9;margin-bottom:3px">'
            f'<span style="font-size:13px;font-weight:500;color:#1e293b">{nm}</span>'
            f'<div style="display:flex;align-items:center;gap:14px">'
            f'<span style="font-size:11px;color:#94a3b8">{r["pontuacao_obtida"]:.0f}/{r["pontuacao_maxima"]:.0f} pts</span>'
            f'<span style="font-size:15px;font-weight:700;color:{cor}">{fmt_pct(r["iaf"])}</span>'
            f'<span style="background:{cor};color:white;padding:2px 8px;border-radius:10px;font-size:11px">{em} {r["classificacao"]}</span>'
            f'</div></div>', unsafe_allow_html=True)
    st.markdown("")
    _status_arquivos(cs)

def _status_arquivos(cs):
    with st.expander("📁 Status dos Arquivos", expanded=False):
        logs=get_logs_upload(cs['id']); arqs_ok={l['arquivo'] for l in logs}; arqs_data={l['arquivo']:l['data_upload'] for l in logs}
        cols=st.columns(4)
        for i,a in enumerate(ARQS):
            ok=a in arqs_ok; cor="#16a34a" if ok else "#dc2626"
            with cols[i%4]:
                st.markdown(f'<div style="padding:6px 10px;border-radius:6px;border:1px solid {cor}22;background:{cor}11;margin-bottom:4px;font-size:12px">{"✅" if ok else "❌"} <b>{a}</b><br><span style="color:{cor}">{arqs_data.get(a,"")[:16] if ok else "Aguardando"}</span></div>',unsafe_allow_html=True)
        falt=[a for a in ARQS if a not in arqs_ok]
        if falt: st.warning(f"Pendentes: {', '.join(falt)}")
        else: st.success("Todos carregados!")

# =============================================
# PÁGINA BASE
# =============================================
def pg_base(ciclo_id):
    st.markdown("### Supervisoras de Base")
    st.markdown("---")
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==ciclo_id),ciclo) if ciclo_id else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    sb_list=get_setores(tipo='base')
    if not sb_list: st.info("Nenhum setor Base configurado."); return
    res_all=get_resultados(cs['id'],tipo='base')
    metas={m['setor_id']:m for m in get_metas(cs['id'])}
    ids_ativos={s['id'] for s in sb_list}
    res=[r for r in res_all if r['setor_id'] in ids_ativos]
    res_d={r['setor_id']:r for r in res}
    sid_nm={s['id']:s['nome'] for s in sb_list}
    t_meta=sum(int(metas.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in sb_list)
    t_real=sum(int(metas.get(s['id'],{}).get('realizado_inicios_reinicios',0)) for s in sb_list)
    pct_g=t_real/t_meta*100 if t_meta>0 else 0
    cor_g="#16a34a" if pct_g>=100 else ("#d97706" if pct_g>=95 else "#dc2626")
    grupo_batido=t_meta>0 and t_real>=t_meta
    # Buscar Base Atual e Base Meta PEF
    base_atual=int(get_config(f"base_atual_{cs['id']}",0) or 0)
    base_meta_pef=int(get_config(f"base_meta_pef_{cs['id']}",0) or 0)
    gap=base_meta_pef-base_atual
    cor_gap="#16a34a" if gap>=0 else "#dc2626"
    # KPIs
    c1,c2,c3,c4=st.columns(4)
    with c1: card_kpi("Meta do Grupo",f"{t_real} / {t_meta}",f"{fmt_pct(pct_g)} atingido",cor_g)
    with c2: card_kpi("Bônus Grupo","✅ Conquistado" if grupo_batido else "❌ Não conquistado","+200 pts" if grupo_batido else f"Faltam {t_meta-t_real}","#16a34a" if grupo_batido else "#dc2626")
    with c3: card_kpi("Base Atual",fmt_int(base_atual),f"Meta PEF: {fmt_int(base_meta_pef)}","#1a2e4a")
    with c4: card_kpi("Gap / Bônus",f"{'+' if gap>=0 else ''}{fmt_int(gap)}","positivo = bônus" if gap>=0 else "negativo = gap",cor_gap)
    st.markdown("")
    # Ranking
    st.markdown("#### 🏆 Ranking Individual")
    c_ant=next((c for c in ciclos if c['id']<cs['id']),None)
    r_ant={r['setor_id']:r for r in get_resultados(c_ant['id'],tipo='base')} if c_ant else {}
    res_sorted=sorted(res,key=lambda x:x['iaf'],reverse=True)
    for pos,r in enumerate(res_sorted,1):
        sid=r['setor_id']; nome=sid_nm.get(sid,str(sid)); meta=metas.get(sid,{})
        real_ir=int(meta.get('realizado_inicios_reinicios',0)); meta_ir=int(meta.get('meta_inicios_reinicios',0))
        contrib=real_ir/t_meta*100 if t_meta>0 else 0
        delta=round(r['iaf']-r_ant[sid]['iaf'],1) if sid in r_ant else None
        extra=f"I+R: {real_ir}/{meta_ir} | Contrib: {fmt_pct(contrib)}"
        linha_rank(pos,nome,r['iaf'],r['classificacao'],delta,extra)
    st.markdown("")
    # Gráfico contribuição
    if res and t_meta>0:
        st.markdown("#### 📊 Contribuição para Meta do Grupo")
        dados_c=[]
        for r in res_sorted:
            sid=r['setor_id']; meta=metas.get(sid,{})
            real_ir=int(meta.get('realizado_inicios_reinicios',0))
            dados_c.append({'Supervisora':sid_nm.get(sid,str(sid)),'Contrib':real_ir/t_meta*100,'Real':real_ir})
        fig=go.Figure()
        for i,d in enumerate(dados_c):
            cor_list=['#1a2e4a','#F9A825','#64748b','#92400e','#16a34a','#dc2626','#7c3aed','#0891b2']
            fig.add_trace(go.Bar(name=d['Supervisora'],x=[d['Contrib']],y=['Grupo'],orientation='h',
                marker_color=cor_list[i%len(cor_list)],
                text=f"{d['Supervisora']}: {d['Real']} ({d['Contrib']:.1f}%)",textposition='inside',insidetextanchor='middle',showlegend=True))
        fig.add_vline(x=100,line_dash="dash",line_color="#475569",annotation_text="Meta 100%")
        fig.update_layout(barmode='stack',height=110,margin=dict(t=10,b=10,l=10,r=10),
            xaxis_ticksuffix="%",plot_bgcolor='white',paper_bgcolor='white',
            legend=dict(orientation="h",yanchor="bottom",y=1.1,xanchor="left",x=0,font=dict(size=11)))
        st.plotly_chart(fig,use_container_width=True)
    # Evolução IAF com linha de meta
    st.markdown("#### 📈 Evolução I+R por Ciclo")
    evol=[]
    for c in ciclos[-6:]:
        metas_c={m['setor_id']:m for m in get_metas(c['id'])}
        for r in get_resultados(c['id'],tipo='base'):
            nm=sid_nm.get(r['setor_id'],str(r['setor_id']))
            meta_c=metas_c.get(r['setor_id'],{})
            evol.append({'Ciclo':c['nome'],'Supervisora':nm,'I+R':r['inicios_reinicios'],'Meta':int(meta_c.get('meta_inicios_reinicios',0))})
    if evol:
        df_e=pd.DataFrame(evol)
        fig2=px.line(df_e,x='Ciclo',y='I+R',color='Supervisora',markers=True,color_discrete_sequence=['#1a2e4a','#F9A825','#64748b','#92400e','#16a34a'])
        fig2.update_layout(height=300,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white')
        st.plotly_chart(fig2,use_container_width=True)

# =============================================
# PÁGINA FINANCEIRO
# =============================================
def pg_financeiro(ciclo_id):
    st.markdown("### Supervisoras de Financeiro")
    st.markdown("---")
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==ciclo_id),ciclo) if ciclo_id else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    sf_list=get_setores(tipo='financeiro')
    if not sf_list: st.info("Nenhum setor Financeiro configurado."); return
    res_all=get_resultados(cs['id'],tipo='financeiro')
    metas={m['setor_id']:m for m in get_metas(cs['id'])}
    ids_ativos_fin={s['id'] for s in sf_list}
    res=[r for r in res_all if r['setor_id'] in ids_ativos_fin]
    todos_setores=get_supabase().table("setores").select("id,nome").execute().data or []
    sid_nm={s['id']:s['nome'] for s in todos_setores}
    c_ant=next((c for c in ciclos if c['id']<cs['id']),None)
    r_ant={r['setor_id']:r for r in get_resultados(c_ant['id'],tipo='financeiro')} if c_ant else {}
    if not res: st.info("Sem dados para este ciclo."); return
    df_res=pd.DataFrame(res)
    mc=['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make']
    receita_total=sum(df_res[c].sum() for c in mc)
    total_ativos=int(df_res['ativos'].sum())
    pct_multi_med=df_res['pct_multimarcas'].mean()
    pct_ativ_med=df_res['pct_atividade'].mean()
    meta_rec=sum(float(metas.get(s['id'],{}).get(f'meta_{m}',0)) for s in sf_list for m in ['boticario','eudora','oui','qdb','cabelos','make'])
    meta_multi=sum(float(metas.get(s['id'],{}).get('meta_multimarcas',0)) for s in sf_list)/len(sf_list) if sf_list else 0
    meta_ativ=sum(float(metas.get(s['id'],{}).get('meta_atividade',0)) for s in sf_list)/len(sf_list) if sf_list else 0
    pct_rec=receita_total/meta_rec*100 if meta_rec>0 else 0
    pct_multi_cum=pct_multi_med/meta_multi*100 if meta_multi>0 else 0
    pct_ativ_cum=pct_ativ_med/meta_ativ*100 if meta_ativ>0 else 0
    # Visão do grupo
    st.markdown("#### 📊 Visão do Grupo")
    c1,c2,c3,c4=st.columns(4)
    cor_r="#16a34a" if pct_rec>=100 else ("#d97706" if pct_rec>=95 else "#dc2626")
    cor_m="#16a34a" if pct_multi_cum>=100 else ("#d97706" if pct_multi_cum>=95 else "#dc2626")
    cor_a="#16a34a" if pct_ativ_cum>=100 else ("#d97706" if pct_ativ_cum>=95 else "#dc2626")
    with c1: card_kpi("Receita Total",fmt_moeda(receita_total),f"meta {fmt_moeda(meta_rec)} ({pct_rec:.0f}%)" if meta_rec>0 else None,cor_r)
    with c2: card_kpi("Ativos",fmt_int(total_ativos))
    with c3: card_kpi("Multimarcas Méd.",fmt_pct(pct_multi_med),f"meta {fmt_pct(meta_multi)} ({pct_multi_cum:.0f}%)" if meta_multi>0 else None,cor_m)
    with c4: card_kpi("Atividade Méd.",fmt_pct(pct_ativ_med),f"meta {fmt_pct(meta_ativ)} ({pct_ativ_cum:.0f}%)" if meta_ativ>0 else None,cor_a)
    st.markdown("")
    # Rankings
    st.markdown("#### 🏆 Rankings por Indicador")
    tab_iaf,tab_multi,tab_ativ,tab_cab,tab_make=st.tabs(["IAF","Multimarcas","Atividade","Cabelos %","Make %"])
    dados_rank=[]
    for r in res:
        nm=sid_nm.get(r['setor_id'],str(r['setor_id'])); meta=metas.get(r['setor_id'],{})
        dados_rank.append({'nome':nm,'iaf':r['iaf'],'classificacao':r['classificacao'],
            'pct_multimarcas':r['pct_multimarcas'],'meta_multimarcas':float(meta.get('meta_multimarcas',0)),
            'pct_atividade':r['pct_atividade'],'meta_atividade':float(meta.get('meta_atividade',0)),
            'pct_cabelos':r['pct_cabelos'],'meta_cabelos':float(meta.get('meta_pct_cabelos',0)),
            'pct_make':r['pct_make'],'meta_make':float(meta.get('meta_pct_make',0)),
            'setor_id':r['setor_id']})
    def mini_rank(dados, key, meta_key, fmt="pct"):
        for pos,d in enumerate(sorted(dados,key=lambda x:x[key],reverse=True),1):
            v=d[key]; m=d[meta_key]; pct=v/m*100 if m>0 else 0
            cor="#16a34a" if pct>=100 else ("#d97706" if pct>=95 else ("#dc2626" if pct>0 else "#94a3b8"))
            ic="🟢" if pct>=100 else ("🟡" if pct>=95 else ("🔴" if pct>0 else "⚪"))
            vs=fmt_pct(v) if fmt=="pct" else fmt_moeda(v)
            ms=fmt_pct(m) if fmt=="pct" else fmt_moeda(m)
            pos_bg=["#F9A825","#94a3b8","#92400e"][pos-1] if pos<=3 else "#e2e8f0"
            pos_txt="white" if pos<=3 else "#475569"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:7px 12px;'
                f'background:white;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:3px">'
                f'<div style="min-width:24px;height:24px;border-radius:50%;background:{pos_bg};'
                f'display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:{pos_txt}">{pos}</div>'
                f'<span style="flex:1;font-size:13px;font-weight:500;color:#1e293b">{d["nome"]}</span>'
                f'<span style="font-size:13px;font-weight:700;color:{cor}">{ic} {vs}</span>'
                f'<span style="font-size:11px;color:#94a3b8">meta {ms} ({pct:.0f}%)</span>'
                f'</div>', unsafe_allow_html=True)
    with tab_iaf:
        res_s=sorted(res,key=lambda x:x['iaf'],reverse=True)
        for pos,r in enumerate(res_s,1):
            delta=round(r['iaf']-r_ant[r['setor_id']]['iaf'],1) if r['setor_id'] in r_ant else None
            atencao=r['iaf']<75
            linha_rank(pos,sid_nm.get(r['setor_id'],str(r['setor_id'])),r['iaf'],r['classificacao'],delta,atencao=atencao)
    with tab_multi: mini_rank(dados_rank,'pct_multimarcas','meta_multimarcas')
    with tab_ativ: mini_rank(dados_rank,'pct_atividade','meta_atividade')
    with tab_cab: mini_rank(dados_rank,'pct_cabelos','meta_cabelos')
    with tab_make: mini_rank(dados_rank,'pct_make','meta_make')
    st.markdown("")
    # Desempenho individual
    st.markdown("#### 📋 Desempenho Individual")
    for r in sorted(res,key=lambda x:x['iaf'],reverse=True):
        sid=r['setor_id']; nome=sid_nm.get(sid,str(sid)); meta=metas.get(sid,{})
        delta=round(r['iaf']-r_ant[sid]['iaf'],1) if sid in r_ant else None
        cor=cor_class(r['classificacao']); em=emoji_class(r['classificacao'])
        atencao=r['iaf']<75
        receita_sup=sum(r.get(cv,0) for cv,_,_ in MARCAS_CFG)
        col1,col2=st.columns([1,1])
        with col1:
            delta_html=""
            if delta is not None:
                dc="#16a34a" if delta>=0 else "#dc2626"
                delta_html=f'<span style="font-size:11px;color:{dc}">{"▲" if delta>=0 else "▼"}{abs(delta):.1f}%</span>'
            warn_html='<span style="font-size:10px;background:#fee2e2;color:#dc2626;padding:1px 6px;border-radius:4px;margin-left:6px">atenção</span>' if atencao else ""
            st.markdown(
                f'<div style="background:white;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border-top:3px solid {cor}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
                f'<span style="font-weight:600;font-size:14px;color:#1e293b">{nome}{warn_html}</span>'
                f'<span style="background:{cor};color:white;padding:2px 8px;border-radius:10px;font-size:11px">{em} {r["classificacao"]}</span>'
                f'</div>'
                f'<div style="text-align:center;margin:10px 0">'
                f'<span style="font-size:36px;font-weight:700;color:{cor}">{fmt_pct(r["iaf"])}</span>'
                f'<div style="font-size:11px;color:#94a3b8;margin-top:2px">{r["pontuacao_obtida"]:.0f}/{r["pontuacao_maxima"]:.0f} pts {delta_html}</div>'
                f'</div>'
                f'<div style="background:#f1f5f9;border-radius:4px;height:6px;overflow:hidden;margin-bottom:10px">'
                f'<div style="background:{cor};width:{min(r["iaf"],100):.1f}%;height:100%;border-radius:4px"></div>'
                f'</div>'
                f'<div style="font-size:12px;color:#64748b;margin-bottom:8px">Receita Total: <b style="color:#1e293b">{fmt_moeda(receita_sup)}</b></div>'
                f'<div style="font-size:12px">',unsafe_allow_html=True)
            indicadores_html=""
            for cv,cm,label in MARCAS_CFG:
                v=r.get(cv,0); m=float(meta.get(cm,0))
                pct=v/m*100 if m>0 else 0
                indicadores_html+=semaforo_linha(pct,label,fmt_moeda(v),fmt_moeda(m))
            for cv,cm,label in INDS_PCT:
                v=r.get(cv,0); m=float(meta.get(cm,0))
                pct=v/m*100 if m>0 else 0
                indicadores_html+=semaforo_linha(pct,label,fmt_pct(v),fmt_pct(m))
            st.markdown(indicadores_html+"</div></div>",unsafe_allow_html=True)
        with col2:
            categorias=['Boticário','Eudora','OUI','QDB','Cabelos','Make','Multimarcas','Atividade']
            metas_radar=[float(meta.get(k,0)) for k in ['meta_boticario','meta_eudora','meta_oui','meta_qdb','meta_cabelos','meta_make','meta_multimarcas','meta_atividade']]
            vals_radar=[min(r.get(cv,0)/m*100,150) if m>0 else 0 for (cv,_,_),m in zip(
                [('valor_boticario','',''),('valor_eudora','',''),('valor_oui','',''),('valor_qdb','',''),
                 ('valor_cabelos','',''),('valor_make','',''),('pct_multimarcas','',''),('pct_atividade','','')],metas_radar)]
            rgba_map={'Diamante':'rgba(26,46,74,0.15)','Ouro':'rgba(249,168,37,0.15)','Prata':'rgba(100,116,139,0.15)','Bronze':'rgba(146,64,14,0.15)'}
            fig_r=go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=vals_radar+[vals_radar[0]],theta=categorias+[categorias[0]],fill='toself',
                fillcolor=rgba_map.get(r['classificacao'],'rgba(148,163,184,0.15)'),
                line=dict(color=cor,width=2),name=nome))
            fig_r.add_trace(go.Scatterpolar(r=[100]*len(categorias)+[100],theta=categorias+[categorias[0]],
                line=dict(color='#e2e8f0',width=1,dash='dot'),showlegend=False))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,150],ticksuffix="%",tickfont=dict(size=9),gridcolor='#f1f5f9'),
                angularaxis=dict(tickfont=dict(size=10))),
                showlegend=False,height=300,margin=dict(t=20,b=20,l=20,r=20),paper_bgcolor='white')
            st.plotly_chart(fig_r,use_container_width=True)
        st.markdown("")
    # Gráficos evolução
    st.markdown("#### 📈 Evolução de Ativos por Ciclo")
    evol_at=[]
    for c in ciclos[-6:]:
        for rv in get_resultados(c['id'],tipo='financeiro'):
            evol_at.append({'Ciclo':c['nome'],'Supervisora':sid_nm.get(rv['setor_id'],str(rv['setor_id'])),'Ativos':rv['ativos']})
    if evol_at:
        fig_at=px.line(pd.DataFrame(evol_at),x='Ciclo',y='Ativos',color='Supervisora',markers=True,
            color_discrete_sequence=['#1a2e4a','#F9A825','#64748b','#92400e','#16a34a','#dc2626'])
        fig_at.update_layout(height=280,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white')
        st.plotly_chart(fig_at,use_container_width=True)
    st.markdown("#### 📈 Evolução de Receita do Grupo")
    evol_rec=[]
    for c in ciclos[-6:]:
        rv_list=get_resultados(c['id'],tipo='financeiro')
        if rv_list:
            df_rv=pd.DataFrame(rv_list)
            rec=sum(df_rv[cv].sum() for cv,_,_ in MARCAS_CFG)
            evol_rec.append({'Ciclo':c['nome'],'Receita':rec})
    if evol_rec:
        fig_rec=go.Figure(go.Scatter(x=[d['Ciclo'] for d in evol_rec],y=[d['Receita'] for d in evol_rec],
            mode='lines+markers',line=dict(color='#1a2e4a',width=2),marker=dict(size=8,color='#F9A825')))
        fig_rec.update_layout(height=240,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white')
        fig_rec.update_yaxes(tickprefix="R$ ",tickformat=",.0f")
        st.plotly_chart(fig_rec,use_container_width=True)

# =============================================
# PÁGINA ER
# =============================================
def pg_er(ciclo_id):
    requer_perfil("gerencia")
    st.markdown("### ER — Espaço Revendedor")
    st.markdown("---")
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==ciclo_id),ciclo) if ciclo_id else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    res=get_resultados_er(cs['id'])
    if not res: st.info("📊 Sem dados ER para este ciclo."); return
    df=pd.DataFrame(res)
    tp=int(df['total_pedidos'].sum()); tnm=int(df['pedidos_nao_multimarca'].sum())
    df_er_raw=st.session_state.get('df_er_raw',None)
    # Calcular KPIs do ER
    rev_er=0; rev_multi_er=0; rev_make_er=0; rev_cab_er=0
    total_ativos_global=int(get_config(f"ativos_unicos_{cs['id']}",0) or 0)
    if df_er_raw is not None:
        rev_er=df_er_raw['Pessoa'].nunique()
        # Multimarcas no ER
        multi_set=set()
        if 'df_multi_raw' in st.session_state:
            df_m=st.session_state['df_multi_raw']
            multi_set=set(df_m[df_m['is_multimarca']]['CodigoRevendedora'].unique())
        rev_er_set=set(df_er_raw['Pessoa'].unique())
        rev_multi_er=len(rev_er_set&multi_set)
        # Make e Cabelos no ER
        if 'df_make_raw' in st.session_state:
            make_set=set(st.session_state['df_make_raw']['CodigoRevendedora'].unique())
            rev_make_er=len(rev_er_set&make_set)
        if 'df_cab_raw' in st.session_state:
            cab_set=set(st.session_state['df_cab_raw']['CodigoRevendedora'].unique())
            rev_cab_er=len(rev_er_set&cab_set)
    pct_make_er=rev_make_er/total_ativos_global*100 if total_ativos_global>0 else 0
    pct_cab_er=rev_cab_er/total_ativos_global*100 if total_ativos_global>0 else 0
    # KPIs
    c1,c2,c3,c4=st.columns(4)
    with c1: card_kpi("Ativos no ER",fmt_int(rev_er),f"× {fmt_int(total_ativos_global)} ativos total" if total_ativos_global>0 else None,"#1a2e4a")
    with c2: card_kpi("No. RV. Multimarcas",fmt_int(rev_multi_er),"dentre os que vieram ao ER","#F9A825")
    with c3: card_kpi("Compraram Make",f"{fmt_int(rev_make_er)} ({fmt_pct(pct_make_er)})","sobre total ativos","#1a2e4a")
    with c4: card_kpi("Compraram Cabelos",f"{fmt_int(rev_cab_er)} ({fmt_pct(pct_cab_er)})","sobre total ativos","#1a2e4a")
    st.markdown("")
    # Ranking com 3 abas
    st.markdown("#### 🏆 Ranking Multimarca")
    df['pedidos_multimarca']=df['total_pedidos']-df['pedidos_nao_multimarca']
    df['pct_multimarca']=100-df['pct_nao_multimarca']
    tab_multi,tab_cab_r,tab_make_r=st.tabs(["Multimarcas","Cabelos","Make"])
    def ranking_caixa(df_rank, col_val, col_label):
        df_s=df_rank.sort_values(col_val,ascending=False).reset_index(drop=True)
        for pos,row in df_s.iterrows():
            pos_num=pos+1; v=row[col_val]
            cor="#16a34a" if v>=70 else ("#d97706" if v>=50 else "#dc2626")
            ic="🟢" if v>=70 else ("🟡" if v>=50 else "🔴")
            pos_bg=["#F9A825","#94a3b8","#92400e"][pos_num-1] if pos_num<=3 else "#e2e8f0"
            pos_txt="white" if pos_num<=3 else "#475569"
            html=(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;'
                f'background:white;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:4px">'
                f'<div style="min-width:26px;height:26px;border-radius:50%;background:{pos_bg};'
                f'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:{pos_txt}">{pos_num}</div>'
                f'<span style="flex:1;font-size:13px;font-weight:600;color:#1e293b">{row["usuario_finalizacao"]}</span>'
                f'<span style="font-size:12px;color:#94a3b8">{int(row[col_val.replace("pct_","pedidos_")] if "pct_" in col_val else row["pedidos_multimarca"])} pedidos</span>'
                f'<span style="font-size:15px;font-weight:700;color:{cor}">{ic} {fmt_pct(v)}</span>'
                f'</div>'
            )
            st.markdown(html,unsafe_allow_html=True)
    with tab_multi: ranking_caixa(df,'pct_multimarca','Multimarca')
    with tab_cab_r:
        if df_er_raw is not None and 'df_cab_raw' in st.session_state:
            cab_set=set(st.session_state['df_cab_raw']['CodigoRevendedora'].unique())
            df_er_c=df_er_raw.copy(); df_er_c['is_cab']=df_er_c['Pessoa'].isin(cab_set)
            cab_rank=df_er_c.groupby('Usuario de Finalização').agg(total=('Pessoa','count'),cab=('is_cab','sum')).reset_index()
            cab_rank['pct_cab']=cab_rank['cab']/cab_rank['total']*100
            cab_rank['pedidos_cab']=cab_rank['cab']
            for pos,row in cab_rank.sort_values('pct_cab',ascending=False).reset_index(drop=True).iterrows():
                pos_num=pos+1; v=row['pct_cab']
                cor="#16a34a" if v>=70 else ("#d97706" if v>=50 else "#dc2626"); ic="🟢" if v>=70 else ("🟡" if v>=50 else "🔴")
                pos_bg=["#F9A825","#94a3b8","#92400e"][pos_num-1] if pos_num<=3 else "#e2e8f0"
                pos_txt="white" if pos_num<=3 else "#475569"
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:white;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:4px"><div style="min-width:26px;height:26px;border-radius:50%;background:{pos_bg};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:{pos_txt}">{pos_num}</div><span style="flex:1;font-size:13px;font-weight:600;color:#1e293b">{row["Usuario de Finalização"]}</span><span style="font-size:12px;color:#94a3b8">{int(row["cab"])} pedidos</span><span style="font-size:15px;font-weight:700;color:{cor}">{ic} {fmt_pct(v)}</span></div>',unsafe_allow_html=True)
        else: st.info("Reprocesse os dados para ver este ranking.")
    with tab_make_r:
        if df_er_raw is not None and 'df_make_raw' in st.session_state:
            make_set=set(st.session_state['df_make_raw']['CodigoRevendedora'].unique())
            df_er_m=df_er_raw.copy(); df_er_m['is_make']=df_er_m['Pessoa'].isin(make_set)
            make_rank=df_er_m.groupby('Usuario de Finalização').agg(total=('Pessoa','count'),mak=('is_make','sum')).reset_index()
            make_rank['pct_make']=make_rank['mak']/make_rank['total']*100
            for pos,row in make_rank.sort_values('pct_make',ascending=False).reset_index(drop=True).iterrows():
                pos_num=pos+1; v=row['pct_make']
                cor="#16a34a" if v>=70 else ("#d97706" if v>=50 else "#dc2626"); ic="🟢" if v>=70 else ("🟡" if v>=50 else "🔴")
                pos_bg=["#F9A825","#94a3b8","#92400e"][pos_num-1] if pos_num<=3 else "#e2e8f0"
                pos_txt="white" if pos_num<=3 else "#475569"
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:white;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:4px"><div style="min-width:26px;height:26px;border-radius:50%;background:{pos_bg};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:{pos_txt}">{pos_num}</div><span style="flex:1;font-size:13px;font-weight:600;color:#1e293b">{row["Usuario de Finalização"]}</span><span style="font-size:12px;color:#94a3b8">{int(row["mak"])} pedidos</span><span style="font-size:15px;font-weight:700;color:{cor}">{ic} {fmt_pct(v)}</span></div>',unsafe_allow_html=True)
        else: st.info("Reprocesse os dados para ver este ranking.")
    st.markdown("")
    # Tabelas analíticas
    if df_er_raw is not None:
        total_rev=df_er_raw['Pessoa'].nunique()
        col_a,col_b=st.columns(2)
        with col_a:
            bairro_rev=df_er_raw.groupby('Bairro')['Pessoa'].nunique().reset_index()
            bairro_rev.columns=['Bairro','Revendedores']; bairro_rev['%']=bairro_rev['Revendedores']/total_rev*100
            tabela_mini("📍 Por Bairro",bairro_rev.sort_values('Revendedores',ascending=False),'Bairro','%')
        with col_b:
            seg_rev=df_er_raw.groupby('Papel')['Pessoa'].nunique().reset_index()
            seg_rev.columns=['Segmentação','Revendedores']; seg_rev['%']=seg_rev['Revendedores']/total_rev*100
            # Ticket médio por segmentação
            ticket=df_er_raw.groupby('Papel').agg(receita=('ValorPraticado','sum'),revs=('Pessoa','nunique')).reset_index()
            ticket['Ticket']=ticket['receita']/ticket['revs']
            ticket_map={row['Papel']:f"R${row['Ticket']:,.0f}".replace(",",".") for _,row in ticket.iterrows()}
            seg_rev['Ticket']=seg_rev['Segmentação'].map(ticket_map)
            tabela_mini("🏅 Por Segmentação",seg_rev.sort_values('Revendedores',ascending=False),'Segmentação','%','Ticket')
        st.markdown("")
        # Gráfico frequência por dia
        st.markdown("#### 📅 Frequência por Dia")
        dias_pt={0:'Segunda',1:'Terça',2:'Quarta',3:'Quinta',4:'Sexta',5:'Sábado',6:'Domingo'}
        df_er_raw['Data Captação']=pd.to_datetime(df_er_raw['Data Captação'],dayfirst=True,errors='coerce')
        freq=df_er_raw.groupby('Data Captação')['Pessoa'].nunique().reset_index()
        freq.columns=['Data','Revendedores']; freq=freq.dropna(subset=['Data']).sort_values('Data')
        freq['Label']=freq['Data'].dt.strftime('%d/%m')+'('+freq['Data'].dt.dayofweek.map(dias_pt)+')'
        fig3=go.Figure(go.Bar(x=freq['Label'],y=freq['Revendedores'],marker_color='#1a2e4a',text=freq['Revendedores'],textposition='outside'))
        fig3.update_layout(height=340,margin=dict(t=20,b=60),xaxis_tickangle=-45,
            yaxis_title="Revendedores Únicos",plot_bgcolor='white',paper_bgcolor='white')
        st.plotly_chart(fig3,use_container_width=True)
    else:
        st.info("ℹ️ Reprocesse os dados em Configurações → Upload para ver análises detalhadas.")
    # Comparativo e evolução
    st.markdown("#### 📊 Comparativo por Caixa")
    df['pct_multimarca']=100-df['pct_nao_multimarca']
    df_g=df.sort_values('pedidos_multimarca',ascending=False)
    cores=["#16a34a" if p>=70 else ("#d97706" if p>=50 else "#dc2626") for p in df_g['pct_multimarca']]
    fig=go.Figure(go.Bar(x=df_g['usuario_finalizacao'],y=df_g['pct_multimarca'],
        marker_color=cores,text=[fmt_pct(p) for p in df_g['pct_multimarca']],textposition='outside'))
    fig.update_layout(height=320,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white')
    fig.update_yaxes(ticksuffix="%",title="% Multimarca")
    st.plotly_chart(fig,use_container_width=True)
    evol=[]
    for c in ciclos[-6:]:
        for rv in get_resultados_er(c['id']):
            evol.append({'Ciclo':c['nome'],'Caixa':rv['usuario_finalizacao'],'% Multimarca':100-rv['pct_nao_multimarca']})
    if evol:
        st.markdown("#### 📈 Evolução por Ciclo")
        fig2=px.line(pd.DataFrame(evol),x='Ciclo',y='% Multimarca',color='Caixa',markers=True,
            color_discrete_sequence=['#1a2e4a','#F9A825','#64748b','#92400e','#16a34a'])
        fig2.update_layout(height=280,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white')
        fig2.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig2,use_container_width=True)

# =============================================
# PÁGINA CONFIGURAÇÕES
# =============================================
def pg_config():
    requer_perfil("gerencia")
    st.markdown("### Configurações")
    aba=st.radio("",["Setores","Pontuação & IAF","Ciclos & Metas","Upload","Senhas","Logs"],horizontal=True)
    st.markdown("---")
    sb=get_supabase(); usuario=st.session_state.get('usuario','sistema')
    if aba=="Setores":
        st.caption("Setores detectados automaticamente no upload. Defina tipo e status.")
        setores_db=sb.table("setores").select("*").order("nome").execute().data or []
        if not setores_db: st.info("Faça o upload das planilhas primeiro.")
        else:
            for s in setores_db:
                c1,c2,c3,c4=st.columns([3,2,2,1])
                c1.markdown(f"**{s['nome']}**")
                with c2: ti=st.selectbox("Tipo",["financeiro","base"],index=0 if s['tipo']=='financeiro' else 1,key=f"t{s['id']}")
                with c3: at=st.selectbox("Status",["Ativo","Inativo"],index=0 if s['ativo'] else 1,key=f"a{s['id']}")
                with c4:
                    if st.button("💾",key=f"s{s['id']}"):
                        sb.table("setores").update({"tipo":ti,"ativo":at=="Ativo"}).eq("id",s['id']).execute()
                        st.success("✓"); st.rerun()
    elif aba=="Pontuação & IAF":
        st.caption("Ajuste pesos e faixas. Clique em Salvar ao terminar.")
        t1,t2,t3=st.tabs(["Pontuação Base","Pontuação Financeiro","Faixas & IAF"])
        with t1:
            c1,c2=st.columns(2)
            with c1: pts_ir=st.number_input("Inícios+Reinícios (pts)",value=int(get_config('pts_inicios_reinicios',800)),step=50)
            with c2: pts_g=st.number_input("Meta Grupo (pts)",value=int(get_config('pts_meta_grupo',200)),step=50)
        with t2:
            c1,c2=st.columns(2)
            with c1:
                pts_m=st.number_input("Por Marca (pts)",value=int(get_config('pts_por_marca_receita',100)),step=10)
                pts_mu=st.number_input("Multimarcas (pts)",value=int(get_config('pts_multimarcas',100)),step=10)
                pts_c=st.number_input("Cabelos % (pts)",value=int(get_config('pts_pct_cabelos',100)),step=10)
            with c2:
                pts_mk=st.number_input("Make % (pts)",value=int(get_config('pts_pct_make',100)),step=10)
                pts_a=st.number_input("Atividade (pts)",value=int(get_config('pts_atividade',100)),step=10)
                mc_er=st.number_input("Meta máx % não multimarca ER",value=float(get_config('meta_nao_multimarca_caixa',30)))
        with t3:
            c1,c2=st.columns(2)
            with c1:
                st.caption("% da meta para pontuação parcial")
                f50=st.number_input("≥X% → 50% pts",value=int(get_config('faixa_pontuacao_50pct',85)))
                f75=st.number_input("≥X% → 75% pts",value=int(get_config('faixa_pontuacao_75pct',95)))
                f100=st.number_input("≥X% → 100% pts",value=int(get_config('faixa_pontuacao_100pct',100)))
            with c2:
                st.caption("IAF mínimo por classificação (%)")
                br=st.number_input("Bronze ≥",value=int(get_config('faixa_bronze_min',65)))
                pr=st.number_input("Prata ≥",value=int(get_config('faixa_prata_min',75)))
                ou=st.number_input("Ouro ≥",value=int(get_config('faixa_ouro_min',85)))
                di=st.number_input("Diamante ≥",value=int(get_config('faixa_diamante_min',95)))
        if st.button("💾 Salvar",use_container_width=True):
            for k,v in [('pts_inicios_reinicios',pts_ir),('pts_meta_grupo',pts_g),('pts_por_marca_receita',pts_m),
                        ('pts_multimarcas',pts_mu),('pts_pct_cabelos',pts_c),('pts_pct_make',pts_mk),('pts_atividade',pts_a),
                        ('faixa_pontuacao_50pct',f50),('faixa_pontuacao_75pct',f75),('faixa_pontuacao_100pct',f100),
                        ('faixa_bronze_min',br),('faixa_prata_min',pr),('faixa_ouro_min',ou),('faixa_diamante_min',di),
                        ('meta_nao_multimarca_caixa',mc_er)]:
                set_config(k,str(v),usuario)
            st.success("✅ Salvo!")
    elif aba=="Ciclos & Metas":
        tc,tm=st.tabs(["Ciclos","Metas do Período"])
        with tc:
            with st.expander("➕ Novo ciclo"):
                nc=st.text_input("Nome (ex: 05/2026)")
                d1,d2=st.columns(2); di=d1.date_input("Início"); df_c=d2.date_input("Fim")
                if st.button("Criar"):
                    if nc:
                        sb.table("ciclos").insert({"nome":nc,"data_inicio":str(di),"data_fim":str(df_c),"ativo":True}).execute()
                        st.success("Criado!"); st.rerun()
            for c in get_ciclos():
                cc1,cc2,cc3=st.columns([3,2,2])
                cc1.markdown(f"**{c['nome']}**"); cc2.markdown("✅ Ativo" if c['ativo'] else "⬜ Inativo")
                if not c['ativo']:
                    with cc3:
                        if st.button("Ativar",key=f"at{c['id']}"):
                            sb.table("ciclos").update({"ativo":False}).execute()
                            sb.table("ciclos").update({"ativo":True}).eq("id",c['id']).execute(); st.rerun()
        with tm:
            ca=get_ciclo_ativo()
            if not ca: st.warning("Crie um ciclo ativo."); st.stop()
            st.caption(f"Ciclo ativo: **{ca['nome']}**")
            # Base Atual e Meta PEF — campos globais do ciclo
            st.markdown("**Base Total**")
            cb1,cb2=st.columns(2)
            base_atual_v=cb1.number_input("Base Atual",min_value=0,value=int(get_config(f"base_atual_{ca['id']}",0) or 0),key="ba_global")
            base_pef_v=cb2.number_input("Base Meta PEF",min_value=0,value=int(get_config(f"base_meta_pef_{ca['id']}",0) or 0),key="bp_global")
            if st.button("💾 Salvar Base Total"):
                set_config(f"base_atual_{ca['id']}",base_atual_v,usuario)
                set_config(f"base_meta_pef_{ca['id']}",base_pef_v,usuario)
                st.success("Salvo!")
            st.markdown("---")
            setores=get_setores(); mex={m['setor_id']:m for m in get_metas(ca['id'])}
            tb,tf=st.tabs(["Base","Financeiro"])
            with tb:
                for s in [x for x in setores if x['tipo']=='base']:
                    ma=mex.get(s['id'],{})
                    with st.expander(s['nome'],expanded=False):
                        b1,b2=st.columns(2)
                        mir=b1.number_input("Meta I+R",min_value=0,value=int(ma.get('meta_inicios_reinicios',0)),key=f"mir{s['id']}")
                        rir=b2.number_input("Realizado I+R",min_value=0,value=int(ma.get('realizado_inicios_reinicios',0)),key=f"rir{s['id']}")
                        if st.button("💾 Salvar",key=f"sb{s['id']}"):
                            upsert_meta(ca['id'],s['id'],{'meta_inicios_reinicios':mir,'realizado_inicios_reinicios':rir,'updated_by':usuario})
                            st.success("Salvo!")
            with tf:
                for s in [x for x in setores if x['tipo']=='financeiro']:
                    ma=mex.get(s['id'],{})
                    with st.expander(s['nome'],expanded=False):
                        f1,f2,f3=st.columns(3)
                        with f1:
                            st.caption("Receitas R$")
                            mbo=st.number_input("Boticário",min_value=0.0,value=float(ma.get('meta_boticario',0)),key=f"mb{s['id']}")
                            meu=st.number_input("Eudora",min_value=0.0,value=float(ma.get('meta_eudora',0)),key=f"me{s['id']}")
                            mou=st.number_input("OUI",min_value=0.0,value=float(ma.get('meta_oui',0)),key=f"mo{s['id']}")
                            mqd=st.number_input("QDB",min_value=0.0,value=float(ma.get('meta_qdb',0)),key=f"mq{s['id']}")
                            mca=st.number_input("Cabelos R$",min_value=0.0,value=float(ma.get('meta_cabelos',0)),key=f"mc{s['id']}")
                            mma=st.number_input("Make R$",min_value=0.0,value=float(ma.get('meta_make',0)),key=f"mm{s['id']}")
                        with f2:
                            st.caption("Indicadores %")
                            mmu=st.number_input("Multimarcas%",0.0,100.0,float(ma.get('meta_multimarcas',0)),key=f"mmu{s['id']}")
                            mpc=st.number_input("Cabelos%",0.0,100.0,float(ma.get('meta_pct_cabelos',0)),key=f"mpc{s['id']}")
                            mpm=st.number_input("Make%",0.0,100.0,float(ma.get('meta_pct_make',0)),key=f"mpm{s['id']}")
                            mat=st.number_input("Atividade%",0.0,100.0,float(ma.get('meta_atividade',0)),key=f"mat{s['id']}")
                        with f3:
                            st.caption("Base")
                            mtb=st.number_input("Tamanho Base",0,value=int(ma.get('tamanho_base',0)),key=f"mtb{s['id']}")
                        if st.button("💾 Salvar",key=f"sf{s['id']}"):
                            upsert_meta(ca['id'],s['id'],{'meta_boticario':mbo,'meta_eudora':meu,'meta_oui':mou,'meta_qdb':mqd,
                                'meta_cabelos':mca,'meta_make':mma,'meta_multimarcas':mmu,'meta_pct_cabelos':mpc,
                                'meta_pct_make':mpm,'meta_atividade':mat,'tamanho_base':mtb,'updated_by':usuario})
                            st.success("Salvo!")
    elif aba=="Upload":
        requer_perfil("admin")
        st.caption("Carregue as planilhas do ERP para o ciclo ativo.")
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
                    # Sincronizar setores
                    setores_enc=set()
                    for nm in ['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos']:
                        if nm in dfs and 'Setor' in dfs[nm].columns:
                            for s in dfs[nm]['Setor'].dropna().unique(): setores_enc.add(str(s).strip())
                    setores_ex={s['nome'] for s in (sb.table("setores").select("nome").execute().data or [])}
                    novos=setores_enc-setores_ex
                    for s in novos: sb.table("setores").insert({"nome":s,"tipo":"financeiro","ativo":True}).execute()
                    if novos: st.info(f"ℹ️ {len(novos)} novos setores detectados.")
                    cfg={r['chave']:r['valor'] for r in (sb.table("configuracoes").select("chave,valor").execute().data or [])}
                    res_p=processar_ciclo(dfs,get_metas(ca['id']),get_setores(),cfg)
                    for r in res_p['resultados']:
                        r['ciclo_id']=ca['id']; sb.table("resultados").upsert(r,on_conflict="ciclo_id,setor_id").execute()
                    for r in res_p['resultados_er']:
                        r['ciclo_id']=ca['id']; sb.table("resultados_er").upsert(r,on_conflict="ciclo_id,usuario_finalizacao").execute()
                    # Salvar ativos únicos
                    ativos_glob=res_p.get('ativos_unicos_global',0)
                    st.session_state['ativos_unicos_global']=ativos_glob
                    chave_at=f"ativos_unicos_{ca['id']}"
                    ex_at=sb.table("configuracoes").select("id").eq("chave",chave_at).execute()
                    if ex_at.data: sb.table("configuracoes").update({"valor":str(ativos_glob),"updated_by":usuario}).eq("chave",chave_at).execute()
                    else: sb.table("configuracoes").insert({"chave":chave_at,"valor":str(ativos_glob),"updated_by":usuario}).execute()
                    # Salvar dados brutos na sessão
                    if 'ER' in dfs: st.session_state['df_er_raw']=dfs['ER']
                    if 'Make' in dfs: st.session_state['df_make_raw']=dfs['Make']
                    if 'Cabelos' in dfs: st.session_state['df_cab_raw']=dfs['Cabelos']
                    # Salvar multimarcas na sessão
                    if 'Ativos' in dfs:
                        df_multi=calc_multimarcas(dfs['Ativos'],dfs)
                        st.session_state['df_multi_raw']=df_multi
                    for nm in uploaded: log_upload(ca['id'],nm,usuario)
                    st.success(f"✅ {len(uploaded)} arquivo(s) processados com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    elif aba=="Senhas":
        requer_perfil("admin")
        st.warning("⚠️ Alterar senhas afeta todos os usuários.")
        s1,s2,s3=st.columns(3)
        with s1:
            st.caption("Leitura"); nl=st.text_input("Nova",type="password",key="nl")
            if st.button("Alterar",key="al"):
                if nl: set_config('senha_leitura',nl,usuario); st.success("✓")
        with s2:
            st.caption("Gerência"); ng=st.text_input("Nova",type="password",key="ng")
            if st.button("Alterar",key="ag"):
                if ng: set_config('senha_gerencia',ng,usuario); st.success("✓")
        with s3:
            st.caption("Admin"); na=st.text_input("Nova",type="password",key="na")
            if st.button("Alterar",key="aa"):
                if na: set_config('senha_admin',na,usuario); st.success("✓")
    elif aba=="Logs":
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

# =============================================
# MAIN
# =============================================
check_auth()
if not st.session_state.get("perfil"):
    login_screen()
else:
    ciclos=get_ciclos()
    ciclo_ativo=get_ciclo_ativo()
    with st.sidebar:
        iniciais = "".join([p[0].upper() for p in st.session_state.usuario.split()[:2]])
        st.markdown(
            f'<div style="padding:16px 8px 12px">'+
            f'<div style="font-size:15px;font-weight:700;color:white;margin-bottom:12px">💼 Venda Direta</div>'+
            f'<div style="display:flex;align-items:center;gap:10px;padding:10px;background:#2d4a6e;border-radius:8px">'+
            f'<div style="width:32px;height:32px;border-radius:50%;background:#F9A825;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:#1a2e4a;flex-shrink:0">{iniciais}</div>'+
            f'<div><div style="font-size:12px;font-weight:600;color:white">{st.session_state.usuario}</div>'+
            f'<div style="font-size:10px;color:#94a3b8">{st.session_state.perfil}</div></div></div></div>',
            unsafe_allow_html=True)
        if ciclos:
            nomes_ciclos=[c['nome'] for c in ciclos]
            idx_ativo=next((i for i,c in enumerate(ciclos) if c['ativo']),0)
            sel_nome=st.selectbox("Ciclo",nomes_ciclos,index=idx_ativo)
            ciclo_sel=next((c for c in ciclos if c['nome']==sel_nome),ciclo_ativo)
            st.session_state.ciclo_sel_id=ciclo_sel['id'] if ciclo_sel else None
        st.markdown("<hr style='border-color:#2d4a6e;margin:8px 0'>", unsafe_allow_html=True)
        pg=st.radio("",["🏠 Home","👥 Base","💼 Financeiro","🏪 ER","⚙️ Configurações"])
        st.markdown("<hr style='border-color:#2d4a6e;margin:8px 0'>", unsafe_allow_html=True)
        if st.button("Sair",use_container_width=True):
            st.session_state.perfil=None; st.session_state.usuario=None; st.rerun()
    ciclo_id=st.session_state.get('ciclo_sel_id')
    if pg=="🏠 Home": pg_home(ciclo_id)
    elif pg=="👥 Base": pg_base(ciclo_id)
    elif pg=="💼 Financeiro": pg_financeiro(ciclo_id)
    elif pg=="🏪 ER": pg_er(ciclo_id)
    elif pg=="⚙️ Configurações": pg_config()
