import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json as _json
import hashlib

st.set_page_config(page_title="Dashboard Venda Direta", page_icon="💼", layout="wide")

st.markdown("""<style>
    .stApp { background: #ffffff; }
    .block-container { padding-top: 2rem; padding-left: 1.5rem; padding-right: 1.5rem; padding-bottom: 2rem; }
    [data-testid="stSidebar"] { background-color: #0a0a0a !important; min-width: 220px; border-right: 1px solid #1a1a1a; }
    [data-testid="stSidebar"] > div { background-color: #0a0a0a !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] div { color: #64748b !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important; border: none !important;
        color: #64748b !important; text-align: left !important;
        padding: 9px 14px !important; border-radius: 8px !important;
        font-size: 13px !important; width: 100% !important; }
    [data-testid="stSidebar"] .stButton > button:hover { background: #111 !important; color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stSelectbox div { background: #111 !important; border: 1px solid #222 !important; color: #94a3b8 !important; }
    h1,h2,h3,h4 { color: #0f172a !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #f8fafc; border-radius: 8px; padding: 4px; border: 1px solid #e2e8f0; }
    .stTabs [data-baseweb="tab"] { font-size: 12px; border-radius: 6px; padding: 6px 16px; color: #64748b !important; }
    .stTabs [aria-selected="true"] { background: #2563eb !important; color: white !important; }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 16px; background: transparent; }
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; background: #ffffff !important; }
    .stExpander summary { color: #475569 !important; }
    .stDataFrame { border-radius: 8px; }
    p { font-size: 13px; color: #475569; }
    .stMarkdown hr { border-color: #e2e8f0; margin: 0.5rem 0; }
    .stAlert { border-radius: 8px !important; }
    .stTextInput input { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; color: #0f172a !important; }
    .stNumberInput input { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; color: #0f172a !important; }
    .stSelectbox div[data-baseweb="select"] { background: #f8fafc !important; }
    label { color: #475569 !important; font-size: 12px !important; }
    .stFileUploader { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; padding: 8px !important; }
    .stFileUploader label { color: #475569 !important; font-size: 13px !important; font-weight: 500 !important; }
    .stFileUploader section { background: #ffffff !important; border: 1px dashed #cbd5e1 !important; }
    .stFileUploader section span { color: #94a3b8 !important; }
</style>""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets.get("SUPABASE_URL","https://bddjuowbotsybamawsts.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY","eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkZGp1b3dib3RzeWJhbWF3c3RzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzNzE3MjAsImV4cCI6MjA5MTk0NzcyMH0.QHDO0Ebfbx4rcV327g1KXD4Ep-jRstQXil_B6L445VU")

@st.cache_resource
def get_sb(): return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_config(k, d=None):
    try:
        r = get_sb().table("configuracoes").select("valor").eq("chave",k).single().execute()
        return r.data["valor"] if r.data else d
    except: return d

def set_config(k, v, u):
    sb = get_sb(); old = get_config(k)
    ex = sb.table("configuracoes").select("id").eq("chave",k).execute()
    if ex.data: sb.table("configuracoes").update({"valor":str(v),"updated_by":u}).eq("chave",k).execute()
    else: sb.table("configuracoes").insert({"chave":k,"valor":str(v),"updated_by":u}).execute()
    try: sb.table("log_alteracoes").insert({"tabela":"configuracoes","campo":k,"valor_anterior":str(old),"valor_novo":str(v),"usuario":u}).execute()
    except: pass

def _uc(k, v, u):
    sb=get_sb(); ex=sb.table("configuracoes").select("id").eq("chave",k).execute()
    if ex.data: sb.table("configuracoes").update({"valor":str(v),"updated_by":u}).eq("chave",k).execute()
    else: sb.table("configuracoes").insert({"chave":k,"valor":str(v),"updated_by":u}).execute()

def get_ciclos(): return get_sb().table("ciclos").select("*").order("id",desc=True).execute().data or []
def get_ciclo_ativo():
    r = get_sb().table("ciclos").select("*").eq("ativo",True).order("id",desc=True).limit(1).execute()
    return r.data[0] if r.data else None
def get_setores(apenas_ativos=True, tipo=None):
    q = get_sb().table("setores").select("*")
    if apenas_ativos: q = q.eq("ativo",True)
    if tipo: q = q.eq("tipo",tipo)
    return q.order("nome").execute().data or []
def get_metas(cid, sid=None):
    q = get_sb().table("metas").select("*").eq("ciclo_id",cid)
    if sid: q = q.eq("setor_id",sid)
    return q.execute().data or []
def get_resultados(cid, tipo=None):
    q = get_sb().table("resultados").select("*").eq("ciclo_id",cid)
    if tipo: q = q.eq("tipo",tipo)
    return q.execute().data or []
def get_resultados_er(cid): return get_sb().table("resultados_er").select("*").eq("ciclo_id",cid).order("pct_nao_multimarca",desc=True).execute().data or []
def get_logs(cid): return get_sb().table("log_uploads").select("*").eq("ciclo_id",cid).order("data_upload",desc=True).execute().data or []
def log_upload(cid, arq, u): get_sb().table("log_uploads").insert({"ciclo_id":cid,"arquivo":arq,"usuario":u}).execute()
def upsert_meta(cid, sid, d):
    d['ciclo_id']=cid; d['setor_id']=sid
    get_sb().table("metas").upsert(d,on_conflict="ciclo_id,setor_id").execute()

def hash_senha(s): return hashlib.sha256(s.encode()).hexdigest()

def get_usuario(nome, senha):
    try:
        h = hash_senha(senha)
        r = get_sb().table("usuarios").select("*").eq("nome",nome).eq("senha_hash",h).eq("ativo",True).single().execute()
        return r.data if r.data else None
    except: return None

def get_usuarios():
    try: return get_sb().table("usuarios").select("*").order("nome").execute().data or []
    except: return []

def fmt_br(v,dec=2): return f"{v:_.{dec}f}".replace("_","X").replace(".",",").replace("X",".")
def fmt_moeda(v): return f"R$ {fmt_br(v)}"
def fmt_pct(v,dec=1): return f"{v:.{dec}f}%".replace(".",",")
def fmt_int(v): return f"{int(v):,}".replace(",",".")

PERFIS={"consultor":1,"gerencia":2,"admin":3}
def check_auth():
    for k in ["perfil","usuario","ciclo_sel_id","usuario_id"]:
        if k not in st.session_state: st.session_state[k]=None

def requer_perfil(p):
    if PERFIS.get(st.session_state.get("perfil"),0)<PERFIS.get(p,99): st.warning("⛔ Sem permissão.");st.stop()

def cor_class(c): return {'Diamante':'#3b82f6','Ouro':'#f59e0b','Prata':'#94a3b8','Bronze':'#d97706'}.get(c,'#475569')
def emoji_class(c): return {'Diamante':'💎','Ouro':'🥇','Prata':'🥈','Bronze':'🥉'}.get(c,'—')
def class_iaf(iaf,cfg={}):
    if iaf>=float(cfg.get('faixa_diamante_min',95)): return 'Diamante'
    if iaf>=float(cfg.get('faixa_ouro_min',85)): return 'Ouro'
    if iaf>=float(cfg.get('faixa_prata_min',75)): return 'Prata'
    if iaf>=float(cfg.get('faixa_bronze_min',65)): return 'Bronze'
    return 'Não Classificado'

def _cor_ating(pct):
    if pct==0: return "#f8fafc","#64748b"
    if pct>=100: return "#f0fdf4","#166534"
    if pct>=95: return "#fefce8","#854d0e"
    return "#fef2f2","#991b1b"

def calc_pts(r,m,p,f50,f75,f100):
    if m<=0: return 0.0
    pct=r/m*100
    if pct>=f100: return p
    if pct>=f75: return p*0.75
    if pct>=f50: return p*0.50
    return 0.0

def ler_planilha(arq,marca):
    df=pd.read_excel(arq); df['Marca']=marca
    return df[~df['ValorPraticado'].isin([0,6])] if marca=='Oui' else df[df['ValorPraticado']>0]

def calc_multimarcas(df_ativos,dfs):
    at=df_ativos[df_ativos['ValorPraticado']>0].copy()
    cods=set(at['CodigoRevendedora'].unique()); cnt={c:0 for c in cods}
    for m in ['Boticario','Eudora','Oui','QDB']:
        if m in dfs:
            cm=set(dfs[m]['CodigoRevendedora'].unique())
            for c in cods:
                if c in cm: cnt[c]+=1
    multi={c for c,n in cnt.items() if n>=2}
    at['is_multimarca']=at['CodigoRevendedora'].isin(multi)
    return at

def processar_ciclo(dfs,metas_list,setores_list,cfg):
    df_at=dfs.get('Ativos')
    f50=float(cfg.get('faixa_pontuacao_50pct',85));f75=float(cfg.get('faixa_pontuacao_75pct',95));f100=float(cfg.get('faixa_pontuacao_100pct',100))
    pts_ir=float(cfg.get('pts_inicios_reinicios',800));pts_g=float(cfg.get('pts_meta_grupo',200))
    pts_bot=float(cfg.get('pts_boticario',300));pts_eud=float(cfg.get('pts_eudora',300))
    pts_at=float(cfg.get('pts_atividade',150));pts_mu=float(cfg.get('pts_multimarcas',90))
    pts_cab=float(cfg.get('pts_pct_cabelos',90));pts_mak=float(cfg.get('pts_pct_make',70))
    md={m['setor_id']:m for m in metas_list}
    df_multi=calc_multimarcas(df_at,dfs) if df_at is not None else None
    resultados=[]
    for s in setores_list:
        sid,nome,tipo=s['id'],s['nome'],s['tipo']; meta=md.get(sid,{})
        if tipo=='base':
            real=int(meta.get('realizado_inicios_reinicios',0));m_ir=int(meta.get('meta_inicios_reinicios',0))
            pts=calc_pts(real,m_ir,pts_ir,f50,f75,f100)
            resultados.append({'setor_id':sid,'tipo':'base','valor_boticario':0,'valor_eudora':0,'valor_oui':0,'valor_qdb':0,'valor_cabelos':0,'valor_make':0,'pct_multimarcas':0,'pct_cabelos':0,'pct_make':0,'pct_atividade':0,'ativos':0,'inicios_reinicios':real,'pontuacao_obtida':pts,'pontuacao_maxima':pts_ir,'iaf':0.0,'classificacao':'Não Classificado'})
        else:
            vals,po,pm={},0.0,0.0
            for marca,cv,cm_key,pts_marca in [('Boticario','valor_boticario','meta_boticario',pts_bot),('Eudora','valor_eudora','meta_eudora',pts_eud),('Oui','valor_oui','meta_oui',0),('QDB','valor_qdb','meta_qdb',0),('Cabelos','valor_cabelos','meta_cabelos',0),('Make','valor_make','meta_make',0)]:
                df=dfs.get(marca); val=df[df['Setor']==nome]['ValorPraticado'].sum() if df is not None else 0.0
                vals[cv]=val; mv=float(meta.get(cm_key,0))
                if mv>0 and pts_marca>0: po+=calc_pts(val,mv,pts_marca,f50,f75,f100); pm+=pts_marca
            at_s=None;n_at=0
            if df_at is not None:
                at_s=df_at[(df_at['Setor']==nome)&(df_at['ValorPraticado']>0)]; n_at=at_s['CodigoRevendedora'].nunique()
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
            m_at_v=float(meta.get('meta_atividade',0))
            if m_at_v>0: po+=calc_pts(pct_at_v,m_at_v,pts_at,f50,f75,f100); pm+=pts_at
            iaf=po/pm*100 if pm>0 else 0.0
            resultados.append({'setor_id':sid,'tipo':'financeiro',**vals,'pct_multimarcas':round(pct_mu,2),'pct_cabelos':round(pct_cab_v,2),'pct_make':round(pct_mak_v,2),'pct_atividade':round(pct_at_v,2),'ativos':n_at,'inicios_reinicios':0,'pontuacao_obtida':round(po,2),'pontuacao_maxima':round(pm,2),'iaf':round(iaf,2),'classificacao':class_iaf(iaf,cfg)})
    base_res=[r for r in resultados if r['tipo']=='base']
    base_mg=[r for r in base_res if next((s for s in setores_list if s['id']==r['setor_id'] and s.get('meta_grupo') is not False),None)]
    t_real=sum(r['inicios_reinicios'] for r in base_mg)
    t_meta=sum(int(md.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in setores_list if s['tipo']=='base' and s.get('meta_grupo') is not False)
    gb=t_meta>0 and t_real>=t_meta
    for r in base_res:
        r['pontuacao_obtida']+=pts_g if gb else 0; r['pontuacao_maxima']+=pts_g
        r['iaf']=round(r['pontuacao_obtida']/r['pontuacao_maxima']*100 if r['pontuacao_maxima']>0 else 0,2)
        r['classificacao']=class_iaf(r['iaf'],cfg)
    er_res=[]
    if df_at is not None and dfs.get('ER') is not None and df_multi is not None:
        nao_m=set(df_multi[~df_multi['is_multimarca']]['CodigoRevendedora'].unique())
        df_er=dfs['ER'].copy()
        df_er=df_er[(df_er['MeioCaptacao']=='VD+')&(df_er['SituaçãoComercial']=='Entregue')]
        df_er['is_nm']=df_er['Pessoa'].isin(nao_m)
        for u,g in df_er.groupby('Usuario de Finalização'):
            tot=len(g); nm=int(g['is_nm'].sum())
            er_res.append({'usuario_finalizacao':u,'total_pedidos':tot,'pedidos_nao_multimarca':nm,'pct_nao_multimarca':round(nm/tot*100 if tot>0 else 0,2)})
        er_res.sort(key=lambda x:x['pct_nao_multimarca'],reverse=True)
    ativos_unicos=int(df_at['CodigoRevendedora'].nunique()) if df_at is not None else 0
    receita_ativos=float(df_at['ValorPraticado'].sum()) if df_at is not None else 0.0
    return {'resultados':resultados,'resultados_er':er_res,'t_real':t_real,'t_meta':t_meta,'ativos_unicos_global':ativos_unicos,'receita_ativos':receita_ativos}

# =============================================
# COMPONENTES VISUAIS
# =============================================
def card_home(label, valor, meta_str=None, pct=0, delta=None, info=False):
    bg,tc = ("#f8fafc","#64748b") if info else _cor_ating(pct)
    border = "#e2e8f0" if info else f"{tc}44"
    delta_html=""
    if delta is not None:
        dc="#16a34a" if delta>=0 else "#dc2626"
        delta_html=f'<div style="font-size:11px;color:{dc};margin-top:2px">{"▲" if delta>=0 else "▼"} {abs(delta):.1f}%</div>'
    meta_html=f'<div style="font-size:11px;color:{tc};opacity:0.75;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{meta_str}</div>' if meta_str else ""
    pct_html=f'<div style="font-size:11px;color:{tc};font-weight:600;margin-top:1px">{pct:.0f}% atingido</div>' if not info and pct>0 else ""
    return (f'<div style="border:1px solid {border};border-radius:12px;padding:14px 16px;background:{bg};min-height:95px;box-sizing:border-box">'
            f'<div style="font-size:10px;color:{tc};opacity:0.7;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>'
            f'<div style="font-size:20px;font-weight:700;color:{tc};line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{valor}</div>'
            f'{meta_html}{pct_html}{delta_html}</div>')

def badge_iaf(cl):
    colors={'Diamante':('#dbeafe','#1e3a5f'),'Ouro':('#fef3c7','#92400e'),'Prata':('#f1f5f9','#475569'),'Bronze':('#ffedd5','#78350f')}
    bg,tc=colors.get(cl,('#f1f5f9','#64748b'))
    em=emoji_class(cl)
    return f'<span style="background:{bg};color:{tc};padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600">{em} {cl}</span>'

def iaf_color(v):
    if v>=85: return '#4ade80'
    if v>=75: return '#fbbf24'
    return '#f87171'

ARQS=['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos','ER','Vendedor']
MARCAS_CFG=[('valor_boticario','meta_boticario','Boticário'),('valor_eudora','meta_eudora','Eudora'),('valor_oui','meta_oui','OUI'),('valor_qdb','meta_qdb','QDB')]

# =============================================
# LOGIN
# =============================================
def login_screen():
    _,col,_ = st.columns([1,1,1])
    with col:
        st.markdown('<div style="background:#0a0a0a;border:1px solid #1e1e1e;border-radius:12px;padding:32px;margin:40px 0 20px;text-align:center"><div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">💼 Venda Direta</div><div style="font-size:12px;color:#475569">Dashboard de Gestão</div></div>',unsafe_allow_html=True)
        nome=st.text_input("Nome de usuário"); senha=st.text_input("Senha",type="password")
        if st.button("Entrar",use_container_width=True,type="primary"):
            if not nome: st.error("Informe seu nome.")
            else:
                u=get_usuario(nome,senha)
                if u:
                    st.session_state.perfil=u['perfil']
                    st.session_state.usuario=u['nome']
                    st.session_state.usuario_id=u['id']
                    try: get_sb().table("log_acessos").insert({"usuario":u['nome'],"perfil":u['perfil'],"acao":"login"}).execute()
                    except: pass
                    st.rerun()
                else:
                    # Fallback senhas legadas
                    if senha==get_config("senha_admin","admin123"):
                        st.session_state.perfil="admin";st.session_state.usuario=nome
                        try: get_sb().table("log_acessos").insert({"usuario":nome,"perfil":"admin","acao":"login"}).execute()
                        except: pass
                        st.rerun()
                    elif senha==get_config("senha_gerencia","gerencia123"):
                        st.session_state.perfil="gerencia";st.session_state.usuario=nome
                        try: get_sb().table("log_acessos").insert({"usuario":nome,"perfil":"gerencia","acao":"login"}).execute()
                        except: pass
                        st.rerun()
                    else: st.error("Usuário ou senha incorretos.")

# =============================================
# HOME
# =============================================
def pg_home(cid):
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==cid),ciclo) if cid else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    st.markdown(f'<h1 style="color:#0f172a;font-size:22px;font-weight:700;margin-bottom:16px">📊 Indicadores Geral — {cs["nome"]}</h1>',unsafe_allow_html=True)
    res=get_resultados(cs['id'])
    if not res: st.info("📊 Aguardando processamento."); _status_arqs(cs); return
    df=pd.DataFrame(res)
    fin=df[df['tipo']=='financeiro']
    mc=['valor_boticario','valor_eudora','valor_oui','valor_qdb','valor_cabelos','valor_make']
    receita=float(get_config(f"receita_ativos_{cs['id']}",0) or 0)
    if receita==0: receita=df[mc].sum().sum()
    ativos=int(get_config(f"ativos_unicos_{cs['id']}",0) or 0)
    sf=get_setores(tipo='financeiro'); ids_fin={s['id'] for s in sf}
    metas_h={m['setor_id']:m for m in get_metas(cs['id'])}
    total_base=sum(int(metas_h.get(sid,{}).get('tamanho_base',0)) for sid in ids_fin)
    meta_rec=sum(float(metas_h.get(sid,{}).get(f'meta_{m}',0)) for sid in ids_fin for m in ['boticario','eudora','oui','qdb','cabelos','make'])
    meta_ativ=float(get_config(f"meta_atividade_global_{cs['id']}",0) or 0)
    meta_ativos=float(get_config(f"meta_ativos_{cs['id']}",0) or 0)
    meta_rpa=float(get_config(f"meta_rpa_{cs['id']}",0) or 0)
    meta_multi=sum(float(metas_h.get(sid,{}).get('meta_multimarcas',0)) for sid in ids_fin)/len(sf) if sf else 0
    meta_cab=sum(float(metas_h.get(sid,{}).get('meta_pct_cabelos',0)) for sid in ids_fin)/len(sf) if sf else 0
    meta_mak=sum(float(metas_h.get(sid,{}).get('meta_pct_make',0)) for sid in ids_fin)/len(sf) if sf else 0
    pct_ativ=ativos/total_base*100 if total_base>0 else 0
    try: multi_codes=set(_json.loads(get_config(f"multi_global_{cs['id']}","[]") or "[]"))
    except: multi_codes=set()
    try: cab_codes=set(_json.loads(get_config(f"cab_global_{cs['id']}","[]") or "[]"))
    except: cab_codes=set()
    try: make_codes=set(_json.loads(get_config(f"make_global_{cs['id']}","[]") or "[]"))
    except: make_codes=set()
    pct_multi=len(multi_codes)/ativos*100 if ativos>0 and multi_codes else fin['pct_multimarcas'].mean() if len(fin)>0 else 0
    pct_cab=len(cab_codes)/ativos*100 if ativos>0 and cab_codes else fin['pct_cabelos'].mean() if len(fin)>0 else 0
    pct_mak=len(make_codes)/ativos*100 if ativos>0 and make_codes else fin['pct_make'].mean() if len(fin)>0 else 0
    rpa=receita/ativos if ativos>0 else 0
    base_atual=int(get_config(f"base_atual_{cs['id']}",0) or 0)
    base_pef=int(get_config(f"base_meta_pef_{cs['id']}",0) or 0)
    gap=base_atual-base_pef
    pct_rec=receita/meta_rec*100 if meta_rec>0 else 0
    pct_ativ_c=pct_ativ/meta_ativ*100 if meta_ativ>0 else 0
    pct_ativos_c=ativos/meta_ativos*100 if meta_ativos>0 else 0
    pct_multi_c=pct_multi/meta_multi*100 if meta_multi>0 else 0
    pct_cab_c=pct_cab/meta_cab*100 if meta_cab>0 else 0
    pct_mak_c=pct_mak/meta_mak*100 if meta_mak>0 else 0
    pct_rpa_c=rpa/meta_rpa*100 if meta_rpa>0 else 0
    cards=[
        card_home("Receita Total",fmt_moeda(receita),f"Meta: {fmt_moeda(meta_rec)}",pct_rec),
        card_home("Atividade Global",fmt_pct(pct_ativ),f"Meta: {fmt_pct(meta_ativ)}",pct_ativ_c),
        card_home("Ativos",fmt_int(ativos),f"Meta: {fmt_int(int(meta_ativos))}",pct_ativos_c),
        card_home("Penetração Multimarcas",fmt_pct(pct_multi),f"Meta: {fmt_pct(meta_multi)}",pct_multi_c),
        card_home("Penetração Cabelos",fmt_pct(pct_cab),f"Meta: {fmt_pct(meta_cab)}",pct_cab_c),
        card_home("Penetração Make",fmt_pct(pct_mak),f"Meta: {fmt_pct(meta_mak)}",pct_mak_c),
        card_home("RPA",fmt_moeda(rpa),f"Meta: {fmt_moeda(meta_rpa)}",pct_rpa_c),
        card_home("Base Total",fmt_int(base_atual),None,0,None,True),
        card_home("Gap / Bônus",f'{("+" if gap>=0 else "")}{fmt_int(gap)}','base atual - meta PEF',0,None,gap>=0),
    ]
    # Grid 3x3
    for row in range(3):
        cols=st.columns(3)
        for col in range(3):
            idx=row*3+col
            if idx<len(cards):
                with cols[col]: st.markdown(cards[idx],unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>",unsafe_allow_html=True)
    _status_arqs(cs)

def _status_arqs(cs):
    with st.expander("📁 Status dos Arquivos",expanded=False):
        logs=get_logs(cs['id']); ok={l['arquivo'] for l in logs}; dt={l['arquivo']:l['data_upload'] for l in logs}
        arqs_base=['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos','ER','Vendedor']
        cols=st.columns(4)
        for i,a in enumerate(arqs_base):
            c="#4ade80" if a in ok else "#f87171"
            with cols[i%4]: st.markdown(f'<div style="padding:6px 10px;border-radius:6px;background:{c}11;border:1px solid {c}33;margin-bottom:4px;font-size:12px;color:{c}">{"✅" if a in ok else "❌"} {a}<br><span style="font-size:10px;color:#475569">{dt.get(a,"")[:16] if a in ok else "Aguardando"}</span></div>',unsafe_allow_html=True)

# =============================================
# BASE
# =============================================
def pg_base(cid):
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==cid),ciclo) if cid else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    st.markdown('<h1 style="color:white;font-size:22px;font-weight:700;margin-bottom:16px">👥 Supervisoras de Base</h1>',unsafe_allow_html=True)
    sb_list=get_setores(tipo='base')
    if not sb_list: st.info("Nenhum setor Base configurado."); return
    res_all=get_resultados(cs['id'],tipo='base')
    metas={m['setor_id']:m for m in get_metas(cs['id'])}
    ids_at={s['id'] for s in sb_list}
    res=[r for r in res_all if r['setor_id'] in ids_at]
    sid_nm={s['id']:s['nome'] for s in sb_list}
    sb_mg=[s for s in sb_list if s.get('meta_grupo') is not False]
    t_meta=sum(int(metas.get(s['id'],{}).get('meta_inicios_reinicios',0)) for s in sb_mg)
    t_real=sum(int(metas.get(s['id'],{}).get('realizado_inicios_reinicios',0)) for s in sb_mg)
    pct_g=t_real/t_meta*100 if t_meta>0 else 0
    gb=t_meta>0 and t_real>=t_meta
    base_atual=int(get_config(f"base_atual_{cs['id']}",0) or 0)
    base_pef=int(get_config(f"base_meta_pef_{cs['id']}",0) or 0)
    gap=base_atual-base_pef
    # KPIs
    bg_g,tc_g=_cor_ating(pct_g)
    bg_gb="#f0fdf4" if gb else "#fef2f2"; tc_gb="#166534" if gb else "#991b1b"
    bg_gap="#f0fdf4" if gap>=0 else "#fef2f2"; tc_gap="#166534" if gap>=0 else "#991b1b"
    st.markdown(f'''<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:24px;margin-top:8px">
    <div style="border:1px solid {tc_g}44;border-radius:12px;padding:16px;background:{bg_g};min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:{tc_g};opacity:0.7;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Meta do Grupo</div>
        <div style="font-size:22px;font-weight:700;color:{tc_g}">{t_real} / {t_meta}</div>
        <div style="font-size:11px;color:{tc_g};opacity:0.7;margin-top:4px">{fmt_pct(pct_g)} atingido</div></div>
    <div style="border:1px solid {tc_gb}44;border-radius:12px;padding:16px;background:{bg_gb};min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:{tc_gb};opacity:0.7;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Bônus Grupo</div>
        <div style="font-size:16px;font-weight:700;color:{tc_gb}">{"✅ Conquistado" if gb else "❌ Não conquistado"}</div>
        <div style="font-size:11px;color:{tc_gb};opacity:0.7;margin-top:4px">{"+200 pts para todas" if gb else f"Faltam {t_meta-t_real}"}</div></div>
    <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#f8fafc;min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Base Atual</div>
        <div style="font-size:22px;font-weight:700;color:#1e293b">{fmt_int(base_atual)}</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px">Meta PEF: {fmt_int(base_pef)}</div></div>
    <div style="border:1px solid {tc_gap}44;border-radius:12px;padding:16px;background:{bg_gap};min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:{tc_gap};opacity:0.7;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Gap / Bônus</div>
        <div style="font-size:22px;font-weight:700;color:{tc_gap}">{("+" if gap>=0 else "")}{fmt_int(gap)}</div>
        <div style="font-size:11px;color:{tc_gap};opacity:0.7;margin-top:4px">base atual - meta PEF</div></div>
    </div>''',unsafe_allow_html=True)
    # Tabela supervisoras
    res_s=sorted(res,key=lambda x:x['inicios_reinicios'],reverse=True)
    html='<table style="width:100%;border-collapse:collapse">'
    html+=('<thead><tr style="border-bottom:1px solid #e2e8f0">'
           '<th style="text-align:left;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.5px"># Supervisora</th>'
           '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Realizado</th>'
           '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Meta</th>'
           '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">%</th>'
           '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Contrib.</th>'
           '</tr></thead><tbody>')
    for pos,r in enumerate(res_s,1):
        sid=r['setor_id']; nome=sid_nm.get(sid,str(sid)); meta=metas.get(sid,{})
        real_ir=int(meta.get('realizado_inicios_reinicios',0)); meta_ir=int(meta.get('meta_inicios_reinicios',0))
        pct_ir=real_ir/meta_ir*100 if meta_ir>0 else 0
        contrib=real_ir/t_meta*100 if t_meta>0 else 0
        _,tc=_cor_ating(pct_ir)
        pos_bg=["#f59e0b","#94a3b8","#92400e"][pos-1] if pos<=3 else "#e2e8f0"
        pos_tc="black" if pos==1 else ("white" if pos<=3 else "#475569")
        html+=(f'<tr style="border-bottom:1px solid #f1f5f9">'
               f'<td style="padding:10px;text-align:left"><span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:{pos_bg};color:{pos_tc};font-size:11px;font-weight:700;margin-right:10px">{pos}</span>'
               f'<span style="color:#0f172a;font-weight:500;font-size:13px">{nome}</span></td>'
               f'<td style="padding:10px;text-align:center;color:#1e293b;font-size:13px;font-weight:600">{real_ir}</td>'
               f'<td style="padding:10px;text-align:center;color:#94a3b8;font-size:13px">{meta_ir}</td>'
               f'<td style="padding:10px;text-align:center;color:{tc};font-weight:700;font-size:13px">{fmt_pct(pct_ir)}</td>'
               f'<td style="padding:10px;text-align:center;color:#64748b;font-size:12px">{fmt_pct(contrib)}</td>'
               f'</tr>')
    html+='</tbody></table>'
    st.markdown(html,unsafe_allow_html=True)

# =============================================
# FINANCEIRO
# =============================================
def pg_financeiro(cid):
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==cid),ciclo) if cid else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    st.markdown('<h1 style="color:white;font-size:22px;font-weight:700;margin-bottom:16px">💼 Supervisoras de Financeiro</h1>',unsafe_allow_html=True)
    sf_list=get_setores(tipo='financeiro')
    if not sf_list: st.info("Sem setores Financeiro."); return
    res_all=get_resultados(cs['id'],tipo='financeiro')
    metas={m['setor_id']:m for m in get_metas(cs['id'])}
    ids_at={s['id'] for s in sf_list}
    res=[r for r in res_all if r['setor_id'] in ids_at]
    todos_s=get_sb().table("setores").select("id,nome").execute().data or []
    sid_nm={s['id']:s['nome'] for s in todos_s}
    if not res: st.info("Sem dados para este ciclo."); return
    # Tabela ordenável
    st.markdown('<p style="color:#475569;font-size:11px;margin-bottom:8px">Clique no cabeçalho para ordenar</p>',unsafe_allow_html=True)
    rows=[]
    for r in res:
        nm=sid_nm.get(r['setor_id'],str(r['setor_id'])); meta=metas.get(r['setor_id'],{})
        m_bot=float(meta.get('meta_boticario',0)); m_eud=float(meta.get('meta_eudora',0))
        m_mu=float(meta.get('meta_multimarcas',0)); m_cab=float(meta.get('meta_pct_cabelos',0))
        m_mak=float(meta.get('meta_pct_make',0)); m_at=float(meta.get('meta_atividade',0))
        rows.append({
            'Supervisora':nm,'IAF':r['iaf'],'Classificação':r['classificacao'],
            'Bot%':r.get('valor_boticario',0)/m_bot*100 if m_bot>0 else 0,
            'Eud%':r.get('valor_eudora',0)/m_eud*100 if m_eud>0 else 0,
            'OUI_R':r.get('valor_oui',0),'QDB_R':r.get('valor_qdb',0),
            'Multi%':r['pct_multimarcas'],'Multi_meta':m_mu,
            'Cab%':r['pct_cabelos'],'Cab_meta':m_cab,
            'Make%':r['pct_make'],'Make_meta':m_mak,
            'Ativ%':r['pct_atividade'],'Ativ_meta':m_at,
            'Bot_meta':m_bot,'Eud_meta':m_eud
        })
    df_tab=pd.DataFrame(rows).sort_values('IAF',ascending=False)
    iaf_tag='<span style="background:#1e3a5f;color:#93c5fd;padding:1px 5px;border-radius:3px;font-size:9px;font-weight:700;margin-left:4px">IAF</span>'
    import streamlit.components.v1 as _comp
    html='<div style="overflow-x:auto"><table id="fin-table" style="width:100%;border-collapse:collapse;min-width:900px">'
    html+=f'<thead><tr style="border-bottom:1px solid #e2e8f0">'
    headers=[('Supervisora','left'),('IAF'+iaf_tag,'center'),('Boticário'+iaf_tag,'center'),('Eudora'+iaf_tag,'center'),('OUI R$','center'),('QDB R$','center'),('Multimarcas'+iaf_tag,'center'),('Penet. Cab'+iaf_tag,'center'),('Penet. Make'+iaf_tag,'center'),('Atividade'+iaf_tag,'center')]
    for i,(h,align) in enumerate(headers):
        html+=f'<th onclick="sortTable({i})" style="text-align:{align};padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;cursor:pointer" title="Clique para ordenar">{h} <span id="arr{i}">↕</span></th>'
    html+='</tr></thead><tbody>'
    def pct_color(v,m):
        if m==0: return '#475569'
        p=v/m*100
        if p>=100: return '#166534'
        if p>=95: return '#854d0e'
        return '#991b1b'
    for _,r in df_tab.iterrows():
        ic=iaf_color(r['IAF']); cl_badge=badge_iaf(r['Classificação'])
        html+=(f'<tr style="border-bottom:1px solid #f1f5f9">'
               f'<td style="padding:10px;color:#0f172a;font-weight:500;font-size:13px;white-space:nowrap">{r["Supervisora"]} {cl_badge}</td>'
               f'<td style="padding:10px;text-align:center;color:{ic};font-weight:700;font-size:14px">{fmt_pct(r["IAF"])}</td>'
               f'<td style="padding:10px;text-align:center;color:{pct_color(r["Bot%"],100)};font-size:12px;font-weight:600">{fmt_pct(r["Bot%"])}</td>'
               f'<td style="padding:10px;text-align:center;color:{pct_color(r["Eud%"],100)};font-size:12px;font-weight:600">{fmt_pct(r["Eud%"])}</td>'
               f'<td style="padding:10px;text-align:center;color:#475569;font-size:12px">{fmt_moeda(r["OUI_R"])}</td>'
               f'<td style="padding:10px;text-align:center;color:#475569;font-size:12px">{fmt_moeda(r["QDB_R"])}</td>'
               f'<td style="padding:10px;text-align:center;color:{pct_color(r["Multi%"],r["Multi_meta"])};font-size:12px">{fmt_pct(r["Multi%"])}</td>'
               f'<td style="padding:10px;text-align:center;color:{pct_color(r["Cab%"],r["Cab_meta"])};font-size:12px">{fmt_pct(r["Cab%"])}</td>'
               f'<td style="padding:10px;text-align:center;color:{pct_color(r["Make%"],r["Make_meta"])};font-size:12px">{fmt_pct(r["Make%"])}</td>'
               f'<td style="padding:10px;text-align:center;color:{pct_color(r["Ativ%"],r["Ativ_meta"])};font-size:12px">{fmt_pct(r["Ativ%"])}</td>'
               f'</tr>')
    html+='''</tbody></table></div>
<script>
var sortDir={};
function sortTable(col){
  var t=document.getElementById("fin-table");
  if(!t)return;
  var rows=Array.from(t.querySelectorAll("tbody tr"));
  sortDir[col]=!sortDir[col];
  rows.sort(function(a,b){
    var av=a.cells[col]?a.cells[col].textContent.trim():"";
    var bv=b.cells[col]?b.cells[col].textContent.trim():"";
    var an=parseFloat(av.replace(/[^0-9,.-]/g,"").replace(",","."));
    var bn=parseFloat(bv.replace(/[^0-9,.-]/g,"").replace(",","."));
    if(!isNaN(an)&&!isNaN(bn))return sortDir[col]?an-bn:bn-an;
    return sortDir[col]?av.localeCompare(bv,"pt"):bv.localeCompare(av,"pt");
  });
  var tb=t.querySelector("tbody");
  rows.forEach(function(r){tb.appendChild(r);});
  for(var i=0;i<10;i++){var el=document.getElementById("arr"+i);if(el)el.textContent=i===col?(sortDir[col]?"↑":"↓"):"↕";}
}
</script>'''
    _comp.html(html,height=max(400,len(rows)*52+100),scrolling=True)
    # Gráfico evolução Ativos
    st.markdown("<div style='height:24px'></div>",unsafe_allow_html=True)
    st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">Evolução de Ativos por Ciclo</p>',unsafe_allow_html=True)
    evol_at=[]
    for c in sorted(ciclos[-6:],key=lambda x:x['id']):
        for rv in get_resultados(c['id'],tipo='financeiro'):
            evol_at.append({'Ciclo':c['nome'],'Supervisora':sid_nm.get(rv['setor_id'],str(rv['setor_id'])),'Ativos':rv['ativos']})
    if evol_at:
        fig=px.line(pd.DataFrame(evol_at),x='Ciclo',y='Ativos',color='Supervisora',markers=True,color_discrete_sequence=['#2563eb','#f59e0b','#16a34a','#dc2626','#7c3aed','#0891b2'])
        fig.update_layout(height=280,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white',legend=dict(font=dict(color='#475569',size=11)),xaxis=dict(color='#475569',gridcolor='#f1f5f9'),yaxis=dict(color='#475569',gridcolor='#f1f5f9'))
        st.plotly_chart(fig,use_container_width=True)

# =============================================
# IAF
# =============================================
def pg_iaf(cid):
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==cid),ciclo) if cid else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    st.markdown('<h1 style="color:#0f172a;font-size:22px;font-weight:700;margin-bottom:16px">🎯 IAF — Instrumento de Avaliação</h1>',unsafe_allow_html=True)
    cfg={r['chave']:r['valor'] for r in (get_sb().table("configuracoes").select("chave,valor").execute().data or [])}
    res_all=get_resultados(cs['id'])
    if not res_all: st.info("Sem dados para este ciclo."); return
    todos_s=get_sb().table("setores").select("id,nome,tipo").execute().data or []
    sid_nm={s['id']:s['nome'] for s in todos_s}
    sid_tipo={s['id']:s['tipo'] for s in todos_s}
    contagem={'Diamante':0,'Ouro':0,'Prata':0,'Bronze':0,'Não Classificado':0}
    for r in res_all: contagem[r['classificacao']]=contagem.get(r['classificacao'],0)+1
    # Cards classificação
    card_cls=[
        ('Diamante','💎','#f0f9ff','#1e3a5f'),('Ouro','🥇','#fffbeb','#92400e'),
        ('Prata','🥈','#f8fafc','#475569'),('Bronze','🥉','#fff7ed','#78350f'),
        ('Não Classificado','—','#f8fafc','#64748b')
    ]
    html='<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:20px">'
    for cl,em,bg,tc in card_cls:
        html+=(f'<div style="border:1px solid #e2e8f0;border-radius:10px;padding:14px;background:{bg};text-align:center;min-height:85px;box-sizing:border-box">'
               f'<div style="font-size:10px;color:{tc};text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">{cl}</div>'
               f'<div style="font-size:28px;font-weight:700;color:{tc}">{contagem.get(cl,0)}</div>'
               f'<div style="font-size:11px;color:{tc}88;margin-top:4px">{em}</div></div>')
    html+='</div>'
    st.markdown(html,unsafe_allow_html=True)
    # Ranking
    st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">Ranking Geral</p>',unsafe_allow_html=True)
    res_s=sorted(res_all,key=lambda x:x['iaf'],reverse=True)
    faixas={'Diamante':float(cfg.get('faixa_diamante_min',95)),'Ouro':float(cfg.get('faixa_ouro_min',85)),'Prata':float(cfg.get('faixa_prata_min',75)),'Bronze':float(cfg.get('faixa_bronze_min',65))}
    ordem_faixas=['Diamante','Ouro','Prata','Bronze']
    def gap_prox(iaf,cl,pts,mx):
        if cl=='Diamante': return None  # already at top
        if cl in ordem_faixas:
            idx=ordem_faixas.index(cl)
            prox_faixa=ordem_faixas[idx-1]  # next level up
        else:
            prox_faixa='Bronze'  # Não Classificado -> Bronze
        pts_needed=int(faixas[prox_faixa]/100*mx)-pts
        return pts_needed if pts_needed>0 else None
    html_rank='<table style="width:100%;border-collapse:collapse">'
    html_rank+=('<thead><tr style="border-bottom:1px solid #e2e8f0">'
                '<th style="text-align:left;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase"># Supervisora</th>'
                '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Tipo</th>'
                '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">IAF</th>'
                '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Pontuação</th>'
                '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Pts p/ segmentar</th>'
                '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Classificação</th>'
                '</tr></thead><tbody>')
    for pos,r in enumerate(res_s,1):
        nm=sid_nm.get(r['setor_id'],str(r['setor_id']))
        tipo=sid_tipo.get(r['setor_id'],'—').capitalize()
        ic=iaf_color(r['iaf'])
        pts=int(r['pontuacao_obtida']); mx=int(r['pontuacao_maxima'])
        gap_pts=gap_prox(r['iaf'],r['classificacao'],pts,mx)
        gap_str=f'+{gap_pts} pts' if gap_pts else '—'
        gap_c='#64748b' if not gap_pts else ('#16a34a' if gap_pts<=30 else '#d97706' if gap_pts<=80 else '#dc2626')
        pos_bg=["#f59e0b","#94a3b8","#92400e"][pos-1] if pos<=3 else "#e2e8f0"
        pos_tc="black" if pos==1 else ("white" if pos<=3 else "#475569")
        html_rank+=(f'<tr style="border-bottom:1px solid #f1f5f9">'
                    f'<td style="padding:10px"><span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:{pos_bg};color:{pos_tc};font-size:11px;font-weight:700;margin-right:10px">{pos}</span>'
                    f'<span style="color:#0f172a;font-weight:500;font-size:13px">{nm}</span></td>'
                    f'<td style="padding:10px;text-align:center"><span style="font-size:10px;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px">{tipo}</span></td>'
                    f'<td style="padding:10px;text-align:center;color:{ic};font-weight:700;font-size:14px">{fmt_pct(r["iaf"])}</td>'
                    f'<td style="padding:10px;text-align:center;color:#64748b;font-size:12px">{pts} / {mx}</td>'
                    f'<td style="padding:10px;text-align:center;color:{gap_c};font-size:12px;font-weight:600">{gap_str}</td>'
                    f'<td style="padding:10px;text-align:center">{badge_iaf(r["classificacao"])}</td>'
                    f'</tr>')
    html_rank+='</tbody></table>'
    st.markdown(html_rank,unsafe_allow_html=True)
    # Gráfico evolução
    st.markdown("<div style='height:24px'></div>",unsafe_allow_html=True)
    st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">Evolução IAF por Ciclo</p>',unsafe_allow_html=True)
    evol=[]
    for c in sorted(ciclos[-6:],key=lambda x:x['id']):
        for rv in get_resultados(c['id']):
            nm=sid_nm.get(rv['setor_id'],str(rv['setor_id']))
            evol.append({'Ciclo':c['nome'],'Supervisora':nm,'IAF':rv['iaf']})
    if evol:
        fig=px.line(pd.DataFrame(evol),x='Ciclo',y='IAF',color='Supervisora',markers=True,color_discrete_sequence=['#2563eb','#f59e0b','#16a34a','#dc2626','#7c3aed','#0891b2','#ea580c','#db2777'])
        fig.update_layout(height=300,margin=dict(t=10,b=10),plot_bgcolor='white',paper_bgcolor='white',legend=dict(font=dict(color='#475569',size=11)),xaxis=dict(color='#475569',gridcolor='#f1f5f9'),yaxis=dict(color='#475569',gridcolor='#f1f5f9',ticksuffix='%'))
        st.plotly_chart(fig,use_container_width=True)

# =============================================
# ER
# =============================================
def pg_er(cid):
    ciclo=get_ciclo_ativo(); ciclos=get_ciclos()
    cs=next((c for c in ciclos if c['id']==cid),ciclo) if cid else ciclo
    if not cs: st.warning("⚠️ Sem ciclo ativo."); return
    st.markdown('<h1 style="color:#0f172a;font-size:22px;font-weight:700;margin-bottom:16px">🏪 ER — Espaço Revendedor</h1>',unsafe_allow_html=True)
    res=get_resultados_er(cs['id'])
    if not res: st.info("📊 Sem dados ER para este ciclo."); return
    df=pd.DataFrame(res)
    total_ativos=int(get_config(f"ativos_unicos_{cs['id']}",0) or 0)
    rev_er=int(get_config(f"er_rev_total_{cs['id']}",0) or 0)
    rev_multi=int(get_config(f"er_rev_multi_{cs['id']}",0) or 0)
    rev_make=int(get_config(f"er_rev_make_{cs['id']}",0) or 0)
    rev_cab=int(get_config(f"er_rev_cab_{cs['id']}",0) or 0)
    pct_make_er=rev_make/rev_er*100 if rev_er>0 else 0
    pct_cab_er=rev_cab/rev_er*100 if rev_er>0 else 0
    # KPIs
    html_kpi=f'''<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px">
    <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#f8fafc;min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Ativos no ER</div>
        <div style="font-size:22px;font-weight:700;color:#1e293b">{fmt_int(rev_er)}</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px">× {fmt_int(total_ativos)} ativos total</div></div>
    <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#f8fafc;min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">No. RV. Multimarcas</div>
        <div style="font-size:22px;font-weight:700;color:#1e293b">{fmt_int(rev_multi)}</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px">dentre os que vieram ao ER</div></div>
    <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#f8fafc;min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Compraram Make</div>
        <div style="font-size:18px;font-weight:700;color:#1e293b">{fmt_int(rev_make)} ({fmt_pct(pct_make_er)})</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px">de {fmt_int(rev_er)} no ER</div></div>
    <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#f8fafc;min-height:85px;box-sizing:border-box">
        <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Compraram Cabelos</div>
        <div style="font-size:18px;font-weight:700;color:#1e293b">{fmt_int(rev_cab)} ({fmt_pct(pct_cab_er)})</div>
        <div style="font-size:11px;color:#94a3b8;margin-top:4px">de {fmt_int(rev_er)} no ER</div></div>
    </div>'''
    st.markdown(html_kpi,unsafe_allow_html=True)
    # Ranking multimarca
    st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">Ranking por Caixa</p>',unsafe_allow_html=True)
    st.markdown('''<style>
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background: #2563eb !important; color: white !important; }
    .stTabs [data-baseweb="tab"] { color: #475569 !important; }
    </style>''',unsafe_allow_html=True)
    df['pedidos_multi']=df['total_pedidos']-df['pedidos_nao_multimarca']
    df['pct_multi']=100-df['pct_nao_multimarca']
    tab_m,tab_c,tab_mk=st.tabs(["Multimarcas","Cabelos","Make"])
    def rank_caixa_er(dados,col_v,col_n):
        html='<table style="width:100%;border-collapse:collapse">'
        for pos,row in enumerate(sorted(dados,key=lambda x:x[col_v],reverse=True),1):
            v=row[col_v]; n=int(row.get(col_n,0))
            tc='#4ade80' if v>=70 else ('#fbbf24' if v>=50 else '#f87171')
            pb=["#f59e0b","#94a3b8","#92400e"][pos-1] if pos<=3 else "#e2e8f0"
            ptc="black" if pos==1 else ("white" if pos<=3 else "#475569")
            nm=row.get('usuario_finalizacao',row.get('usuario','—'))
            html+=(f'<tr style="border-bottom:1px solid #f1f5f9">'
                   f'<td style="padding:10px"><span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:{pb};color:{ptc};font-size:11px;font-weight:700;margin-right:10px">{pos}</span>'
                   f'<span style="color:#0f172a;font-size:13px;font-weight:500">{nm}</span></td>'
                   f'<td style="padding:10px;text-align:center;color:#475569;font-size:12px">{n} pedidos</td>'
                   f'<td style="padding:10px;text-align:center;color:{tc};font-weight:700;font-size:15px">{fmt_pct(v)}</td></tr>')
        html+='</table>'
        st.markdown(html,unsafe_allow_html=True)
    with tab_m:
        dados_m=[{'usuario_finalizacao':r['usuario_finalizacao'],'pct_multi':100-r['pct_nao_multimarca'],'pedidos_multi':r['total_pedidos']-r['pedidos_nao_multimarca']} for _,r in df.iterrows()]
        rank_caixa_er(dados_m,'pct_multi','pedidos_multi')
    with tab_c:
        rank_cab=_json.loads(get_config(f"er_rank_cab_{cs['id']}","[]") or "[]")
        if rank_cab: rank_caixa_er(rank_cab,'pct_cab','n_cab')
        else: st.info("Reprocesse os dados.")
    with tab_mk:
        rank_mak=_json.loads(get_config(f"er_rank_mak_{cs['id']}","[]") or "[]")
        if rank_mak: rank_caixa_er(rank_mak,'pct_mak','n_mak')
        else: st.info("Reprocesse os dados.")

    # Análise por vendedor
    st.markdown("<div style='height:20px'></div>",unsafe_allow_html=True)
    st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">Análise por Vendedor (conversão)</p>',unsafe_allow_html=True)
    vend_data=_json.loads(get_config(f"er_vend_conv_{cs['id']}","[]") or "[]")
    if vend_data:
        html_v='<table style="width:100%;border-collapse:collapse">'
        html_v+=('<thead><tr style="border-bottom:1px solid #e2e8f0">'
                 '<th style="text-align:left;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Vendedor</th>'
                 '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Atendidos</th>'
                 '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Multimarcas</th>'
                 '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Cabelos</th>'
                 '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Make</th>'
                 '<th style="text-align:center;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Ticket Méd.</th>'
                 '</tr></thead><tbody>')
        for v in sorted(vend_data,key=lambda x:x.get('atendidos',0),reverse=True):
            nm=v.get('vendedor','—'); at=int(v.get('atendidos',0))
            pmu=float(v.get('pct_multi',0)); pcb=float(v.get('pct_cab',0)); pmk=float(v.get('pct_make',0))
            tk=float(v.get('ticket',0))
            def cc(p): return '#166534' if p>=70 else ('#854d0e' if p>=50 else '#991b1b')
            html_v+=(f'<tr style="border-bottom:1px solid #f1f5f9">'
                     f'<td style="padding:10px;color:#0f172a;font-weight:500;font-size:13px">{nm}</td>'
                     f'<td style="padding:10px;text-align:center;color:#94a3b8;font-size:13px">{at}</td>'
                     f'<td style="padding:10px;text-align:center;color:{cc(pmu)};font-size:13px;font-weight:600">{fmt_pct(pmu)}</td>'
                     f'<td style="padding:10px;text-align:center;color:{cc(pcb)};font-size:13px;font-weight:600">{fmt_pct(pcb)}</td>'
                     f'<td style="padding:10px;text-align:center;color:{cc(pmk)};font-size:13px;font-weight:600">{fmt_pct(pmk)}</td>'
                     f'<td style="padding:10px;text-align:center;color:#64748b;font-size:12px">{fmt_moeda(tk)}</td>'
                     f'</tr>')
        html_v+='</tbody></table>'
        st.markdown(html_v,unsafe_allow_html=True)
        # Não convertidos
        st.markdown("<div style='height:16px'></div>",unsafe_allow_html=True)
        st.markdown('<p style="color:#f87171;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">⚠️ Revendedores não convertidos — vendedores responsáveis</p>',unsafe_allow_html=True)
        nao_conv=_json.loads(get_config(f"er_nao_conv_{cs['id']}","[]") or "[]")
        nc_multi=[x for x in nao_conv if x.get('tipo')=='multi']
        nc_cab=[x for x in nao_conv if x.get('tipo')=='cab']
        nc_mak=[x for x in nao_conv if x.get('tipo')=='make']
        st.markdown(f'<span style="color:#64748b;font-size:11px">Multimarcas: {len(nc_multi)} | Cabelos: {len(nc_cab)} | Make: {len(nc_mak)}</span>',unsafe_allow_html=True)
        if nao_conv:
            tab_nm,tab_nc,tab_nmk=st.tabs(["Multimarcas","Cabelos","Make"])
            def tabela_nao_conv(dados,key):
                if not dados: st.info("Todos convertidos! 🎉"); return
                html_nc='<table style="width:100%;border-collapse:collapse">'
                html_nc+=('<thead><tr style="border-bottom:1px solid #e2e8f0">'
                          '<th style="text-align:left;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Revendedor</th>'
                          '<th style="text-align:left;padding:8px 10px;font-size:10px;color:#475569;font-weight:600;text-transform:uppercase">Vendedores que atenderam</th>'
                          '</tr></thead><tbody>')
                for item in dados[:50]:
                    rv=item.get('revendedor','—'); vends=', '.join(item.get('vendedores',[]))
                    html_nc+=(f'<tr style="border-bottom:1px solid #f1f5f9">'
                              f'<td style="padding:8px 10px;color:#1e293b;font-size:12px">{rv}</td>'
                              f'<td style="padding:8px 10px;color:#f87171;font-size:12px">{vends}</td>'
                              f'</tr>')
                html_nc+='</tbody></table>'
                st.markdown(html_nc,unsafe_allow_html=True)
            with tab_nm: tabela_nao_conv(nc_multi,'multi')
            with tab_nc: tabela_nao_conv(nc_cab,'cab')
            with tab_nmk: tabela_nao_conv(nc_mak,'make')
    else:
        st.info("ℹ️ Faça upload da planilha Vendedor para ver análise de conversão por vendedor.")

    # Bairro e segmentação
    st.markdown("<div style='height:20px'></div>",unsafe_allow_html=True)
    bairro_data=_json.loads(get_config(f"er_bairro_{cs['id']}","[]") or "[]")
    seg_data=_json.loads(get_config(f"er_seg_{cs['id']}","[]") or "[]")
    if bairro_data or seg_data:
        col_a,col_b=st.columns(2)
        with col_a:
            st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:6px">📍 Por Bairro</p>',unsafe_allow_html=True)
            html_b='<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">'
            for i,row in enumerate(bairro_data[:15]):
                bg="#f8fafc" if i%2==0 else "white"
                html_b+=f'<div style="display:flex;justify-content:space-between;padding:6px 12px;background:{bg}"><span style="font-size:12px;color:#475569">{row["Bairro"]}</span><span style="font-size:12px;font-weight:700;color:#1e293b">{row["pct"]:.1f}%</span></div>'
            html_b+='</div>'
            st.markdown(html_b,unsafe_allow_html=True)
        with col_b:
            st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:6px">🏅 Por Segmentação</p>',unsafe_allow_html=True)
            html_s='<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><div style="display:flex;justify-content:space-between;padding:5px 12px;background:#111;border-bottom:1px solid #1e1e1e"><span style="font-size:10px;color:#334155;font-weight:700">SEGMENTAÇÃO</span><span style="font-size:10px;color:#334155;font-weight:700">RVs · % · TICKET</span></div>'
            for row in seg_data:
                tk_str=f"R$ {row.get('ticket',0):,.0f}".replace(",",".") if row.get('ticket',0)>0 else "—"
                html_s+=f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 12px;border-bottom:1px solid #f1f5f9"><span style="font-size:12px;color:#94a3b8">{row["seg"]}</span><div style="display:flex;gap:10px;align-items:center"><span style="font-size:12px;color:#64748b">{int(row["rvs"])}</span><span style="font-size:12px;font-weight:700;color:#1e293b">{row["pct"]:.1f}%</span><span style="font-size:11px;color:#475569;min-width:80px;text-align:right">{tk_str}</span></div></div>'
            html_s+='</div>'
            st.markdown(html_s,unsafe_allow_html=True)
    # Frequência por dia
    freq_data=_json.loads(get_config(f"er_freq_{cs['id']}","[]") or "[]")
    if freq_data:
        st.markdown("<div style='height:16px'></div>",unsafe_allow_html=True)
        st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">📅 Frequência por Dia</p>',unsafe_allow_html=True)
        fig3=go.Figure(go.Bar(x=[r['label'] for r in freq_data],y=[r['rvs'] for r in freq_data],marker_color='#2563eb',text=[r['rvs'] for r in freq_data],textposition='outside',textfont=dict(color='#94a3b8')))
        fig3.update_layout(height=280,margin=dict(t=30,b=60),xaxis_tickangle=-45,plot_bgcolor='white',paper_bgcolor='white',xaxis=dict(color='#475569',gridcolor='#f1f5f9'),yaxis=dict(color='#475569',gridcolor='#f1f5f9',title='Revendedores Únicos'))
        st.plotly_chart(fig3,use_container_width=True)
    # Gráfico conversão por vendedor
    if vend_data:
        st.markdown('<p style="color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin-bottom:8px">📊 Conversão por Vendedor</p>',unsafe_allow_html=True)
        df_vd=pd.DataFrame(vend_data)
        fig_v=go.Figure()
        fig_v.add_trace(go.Bar(name='Multimarcas',x=df_vd['vendedor'],y=df_vd['pct_multi'],marker_color='#2563eb',text=[fmt_pct(v) for v in df_vd['pct_multi']],textposition='outside',textfont=dict(color='#475569',size=10)))
        fig_v.add_trace(go.Bar(name='Cabelos',x=df_vd['vendedor'],y=df_vd['pct_cab'],marker_color='#f59e0b',text=[fmt_pct(v) for v in df_vd['pct_cab']],textposition='outside',textfont=dict(color='#475569',size=10)))
        fig_v.add_trace(go.Bar(name='Make',x=df_vd['vendedor'],y=df_vd['pct_make'],marker_color='#16a34a',text=[fmt_pct(v) for v in df_vd['pct_make']],textposition='outside',textfont=dict(color='#475569',size=10)))
        fig_v.update_layout(barmode='group',height=320,margin=dict(t=30,b=10),plot_bgcolor='white',paper_bgcolor='white',legend=dict(font=dict(color='#475569',size=11)),xaxis=dict(color='#475569',gridcolor='#f1f5f9'),yaxis=dict(color='#475569',gridcolor='#f1f5f9',ticksuffix='%',range=[0,110]))
        st.plotly_chart(fig_v,use_container_width=True)

# =============================================
# CONFIGURAÇÕES
# =============================================
def pg_config():
    requer_perfil("gerencia")
    st.markdown('<h1 style="color:#0f172a;font-size:22px;font-weight:700;margin-bottom:16px">⚙️ Configurações</h1>',unsafe_allow_html=True)
    aba=st.radio("",["Setores","Pontuação & IAF","Ciclos & Metas","Upload","Usuários","Logs"],horizontal=True)
    st.markdown("<hr style='border-color:#1e1e1e;margin:8px 0 16px'>",unsafe_allow_html=True)
    sb=get_sb(); usuario=st.session_state.get('usuario','sistema')
    if aba=="Setores":
        requer_perfil("admin")
        sdb=sb.table("setores").select("*").order("nome").execute().data or []
        if not sdb: st.info("Faça o upload primeiro.")
        else:
            h1,h2,h3,h4,h5=st.columns([3,2,2,2,1])
            for h,lbl in zip([h1,h2,h3,h4],['SETOR','TIPO','STATUS','META GRUPO']):
                h.markdown(f'<span style="font-size:11px;color:#475569;font-weight:700">{lbl}</span>',unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#1e1e1e;margin:4px 0'>",unsafe_allow_html=True)
            for s in sdb:
                c1,c2,c3,c4,c5=st.columns([3,2,2,2,1])
                c1.markdown(f'<div style="padding-top:8px;font-size:13px;color:white">{s["nome"]}</div>',unsafe_allow_html=True)
                with c2: ti=st.selectbox("",["financeiro","base"],index=0 if s['tipo']=='financeiro' else 1,key=f"t{s['id']}",label_visibility="collapsed")
                with c3: at=st.selectbox("",["Ativo","Inativo"],index=0 if s['ativo'] else 1,key=f"a{s['id']}",label_visibility="collapsed")
                with c4: mg=st.selectbox("",["Sim","Não"],index=0 if s.get('meta_grupo',True) else 1,key=f"mg{s['id']}",label_visibility="collapsed")
                with c5:
                    if st.button("💾",key=f"s{s['id']}"): sb.table("setores").update({"tipo":ti,"ativo":at=="Ativo","meta_grupo":mg=="Sim"}).eq("id",s['id']).execute(); st.success("✓"); st.rerun()
    elif aba=="Pontuação & IAF":
        requer_perfil("admin")
        t1,t2,t3=st.tabs(["Pontuação Base","Pontuação Financeiro","Faixas & IAF"])
        with t1:
            c1,c2=st.columns(2)
            with c1: pts_ir=st.number_input("Inícios+Reinícios (pts)",value=int(get_config('pts_inicios_reinicios',800)),step=50)
            with c2: pts_g=st.number_input("Meta Grupo (pts)",value=int(get_config('pts_meta_grupo',200)),step=50)
        with t2:
            c1,c2=st.columns(2)
            with c1:
                pts_bot=st.number_input("Boticário (pts)",value=int(get_config('pts_boticario',300)),step=10)
                pts_eud=st.number_input("Eudora (pts)",value=int(get_config('pts_eudora',300)),step=10)
                pts_at2=st.number_input("Atividade (pts)",value=int(get_config('pts_atividade',150)),step=10)
            with c2:
                pts_mu=st.number_input("Multimarcas (pts)",value=int(get_config('pts_multimarcas',90)),step=10)
                pts_cab=st.number_input("Cabelos % (pts)",value=int(get_config('pts_pct_cabelos',90)),step=10)
                pts_mak=st.number_input("Make % (pts)",value=int(get_config('pts_pct_make',70)),step=10)
            st.info(f"Total: {pts_bot+pts_eud+pts_at2+pts_mu+pts_cab+pts_mak} pts (meta: 1.000)")
        with t3:
            c1,c2=st.columns(2)
            with c1:
                f50=st.number_input("≥X% → 50% pts",value=int(get_config('faixa_pontuacao_50pct',85)))
                f75=st.number_input("≥X% → 75% pts",value=int(get_config('faixa_pontuacao_75pct',95)))
                f100=st.number_input("≥X% → 100% pts",value=int(get_config('faixa_pontuacao_100pct',100)))
            with c2:
                br=st.number_input("Bronze ≥",value=int(get_config('faixa_bronze_min',65)))
                pr=st.number_input("Prata ≥",value=int(get_config('faixa_prata_min',75)))
                ou=st.number_input("Ouro ≥",value=int(get_config('faixa_ouro_min',85)))
                di=st.number_input("Diamante ≥",value=int(get_config('faixa_diamante_min',95)))
        if st.button("💾 Salvar",use_container_width=True):
            for k,v in [('pts_inicios_reinicios',pts_ir),('pts_meta_grupo',pts_g),('pts_boticario',pts_bot),('pts_eudora',pts_eud),('pts_atividade',pts_at2),('pts_multimarcas',pts_mu),('pts_pct_cabelos',pts_cab),('pts_pct_make',pts_mak),('faixa_pontuacao_50pct',f50),('faixa_pontuacao_75pct',f75),('faixa_pontuacao_100pct',f100),('faixa_bronze_min',br),('faixa_prata_min',pr),('faixa_ouro_min',ou),('faixa_diamante_min',di)]:
                set_config(k,str(v),usuario)
            st.success("✅ Salvo!")
    elif aba=="Ciclos & Metas":
        tc,tm=st.tabs(["Ciclos","Metas do Período"])
        with tc:
            with st.expander("➕ Novo ciclo"):
                nc=st.text_input("Nome (ex: 05/2026)"); d1,d2=st.columns(2); di=d1.date_input("Início"); dfc=d2.date_input("Fim")
                if st.button("Criar"):
                    if nc: sb.table("ciclos").insert({"nome":nc,"data_inicio":str(di),"data_fim":str(dfc),"ativo":True}).execute(); st.success("Criado!"); st.rerun()
            for c in get_ciclos():
                cc1,cc2,cc3=st.columns([3,2,2]); cc1.markdown(f'<span style="color:white">{c["nome"]}</span>',unsafe_allow_html=True); cc2.markdown("✅ Ativo" if c['ativo'] else "⬜ Inativo")
                if not c['ativo']:
                    with cc3:
                        if st.button("Ativar",key=f"at{c['id']}"): sb.table("ciclos").update({"ativo":False}).execute(); sb.table("ciclos").update({"ativo":True}).eq("id",c['id']).execute(); st.rerun()
        with tm:
            ca=get_ciclo_ativo()
            if not ca: st.warning("Crie um ciclo ativo."); st.stop()
            st.markdown(f'<span style="color:#475569;font-size:12px">Ciclo ativo: </span><span style="color:white;font-weight:600">{ca["nome"]}</span>',unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
            st.markdown('<span style="color:#94a3b8;font-size:12px;font-weight:600">Metas Globais</span>',unsafe_allow_html=True)
            mg1,mg2,mg3,mg4,mg5=st.columns(5)
            ba_v=mg1.number_input("Base Atual",min_value=0,value=int(get_config(f"base_atual_{ca['id']}",0) or 0),key="ba")
            bp_v=mg2.number_input("Meta PEF",min_value=0,value=int(get_config(f"base_meta_pef_{ca['id']}",0) or 0),key="bp")
            mag_v=mg3.number_input("Meta Atividade %",min_value=0.0,max_value=100.0,value=float(get_config(f"meta_atividade_global_{ca['id']}",0) or 0),step=0.1,key="mag")
            mat_v=mg4.number_input("Meta Ativos",min_value=0,value=int(float(get_config(f"meta_ativos_{ca['id']}",0) or 0)),key="mat")
            mrpa_v=mg5.number_input("Meta RPA (R$)",min_value=0.0,value=float(get_config(f"meta_rpa_{ca['id']}",0) or 0),step=10.0,key="mrpa")
            if st.button("💾 Salvar Metas Globais"):
                for k,v in [(f"base_atual_{ca['id']}",ba_v),(f"base_meta_pef_{ca['id']}",bp_v),(f"meta_atividade_global_{ca['id']}",mag_v),(f"meta_ativos_{ca['id']}",mat_v),(f"meta_rpa_{ca['id']}",mrpa_v)]:
                    set_config(k,str(v),usuario)
                st.success("Salvo!")
            st.markdown("<hr style='border-color:#1e1e1e;margin:12px 0'>",unsafe_allow_html=True)
            setores=get_setores(); mex={m['setor_id']:m for m in get_metas(ca['id'])}
            tb,tf=st.tabs(["Base","Financeiro"])
            with tb:
                for s in [x for x in setores if x['tipo']=='base']:
                    ma=mex.get(s['id'],{})
                    with st.expander(s['nome'],expanded=False):
                        b1,b2=st.columns(2)
                        mir=b1.number_input("Meta I+R",min_value=0,value=int(ma.get('meta_inicios_reinicios',0)),key=f"mir{s['id']}")
                        rir=b2.number_input("Realizado I+R",min_value=0,value=int(ma.get('realizado_inicios_reinicios',0)),key=f"rir{s['id']}")
                        if st.button("💾 Salvar",key=f"sb{s['id']}"): upsert_meta(ca['id'],s['id'],{'meta_inicios_reinicios':mir,'realizado_inicios_reinicios':rir,'updated_by':usuario}); st.success("Salvo!")
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
                            mat=st.number_input("Atividade%",0.0,100.0,float(ma.get('meta_atividade',0)),key=f"mat_s{s['id']}")
                        with f3:
                            st.caption("Base")
                            mtb=st.number_input("Tamanho Base",0,value=int(ma.get('tamanho_base',0)),key=f"mtb{s['id']}")
                        if st.button("💾 Salvar",key=f"sf{s['id']}"): upsert_meta(ca['id'],s['id'],{'meta_boticario':mbo,'meta_eudora':meu,'meta_oui':mou,'meta_qdb':mqd,'meta_cabelos':mca,'meta_make':mma,'meta_multimarcas':mmu,'meta_pct_cabelos':mpc,'meta_pct_make':mpm,'meta_atividade':mat,'tamanho_base':mtb,'updated_by':usuario}); st.success("Salvo!")
    elif aba=="Upload":
        requer_perfil("admin")
        ca=get_ciclo_ativo()
        if not ca: st.warning("Sem ciclo ativo."); return
        st.markdown(f'<span style="color:#94a3b8;font-size:13px">Ciclo: <b style="color:white">{ca["nome"]}</b></span>',unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
        uploaded={}
        arqs_labels={'Boticario':'Boticário','Cabelos':'Cabelos','Eudora':'Eudora','Make':'Make','Oui':'OUI','QDB':'QDB','Ativos':'Ativos','ER':'ER','Vendedor':'Vendedor (itens por vendedor)'}
        c1u,c2u=st.columns(2)
        for i,(nm,lbl) in enumerate(arqs_labels.items()):
            with (c1u if i%2==0 else c2u):
                st.markdown(f'<div style="font-size:13px;color:#94a3b8;font-weight:500;margin-bottom:4px">📁 {lbl}</div>',unsafe_allow_html=True)
                f=st.file_uploader(f"Selecionar {lbl}",type=['xlsx'],key=f"up{nm}",label_visibility="collapsed")
                if f: uploaded[nm]=f
        if uploaded and st.button("🚀 Processar",use_container_width=True,type="primary"):
            with st.spinner("Processando..."):
                try:
                    dfs={}
                    for nm,arq in uploaded.items():
                        if nm in ['ER','Ativos','Vendedor']: dfs[nm]=pd.read_excel(arq)
                        else: dfs[nm]=ler_planilha(arq,nm)
                    se=set()
                    for nm in ['Boticario','Cabelos','Eudora','Make','Oui','QDB','Ativos']:
                        if nm in dfs and 'Setor' in dfs[nm].columns:
                            for s in dfs[nm]['Setor'].dropna().unique(): se.add(str(s).strip())
                    ex_s={s['nome'] for s in (sb.table("setores").select("nome").execute().data or [])}
                    for s in se-ex_s: sb.table("setores").insert({"nome":s,"tipo":"financeiro","ativo":True,"meta_grupo":True}).execute()
                    cfg={r['chave']:r['valor'] for r in (sb.table("configuracoes").select("chave,valor").execute().data or [])}
                    rp=processar_ciclo(dfs,get_metas(ca['id']),get_setores(),cfg)
                    for r in rp['resultados']: r['ciclo_id']=ca['id']; sb.table("resultados").upsert(r,on_conflict="ciclo_id,setor_id").execute()
                    sb.table("resultados_er").delete().eq("ciclo_id",ca['id']).execute()
                    for r in rp['resultados_er']: r['ciclo_id']=ca['id']; sb.table("resultados_er").insert(r).execute()
                    ag=rp.get('ativos_unicos_global',0)
                    _uc(f"ativos_unicos_{ca['id']}",ag,usuario)
                    _uc(f"receita_ativos_{ca['id']}",rp.get('receita_ativos',0),usuario)
                    if 'Make' in dfs:
                        mk=[int(x) for x in dfs['Make'][dfs['Make']['ValorPraticado']>0]['CodigoRevendedora'].dropna().unique()]
                        _uc(f"make_global_{ca['id']}",_json.dumps(mk),usuario)
                    if 'Cabelos' in dfs:
                        cb=[int(x) for x in dfs['Cabelos'][dfs['Cabelos']['ValorPraticado']>0]['CodigoRevendedora'].dropna().unique()]
                        _uc(f"cab_global_{ca['id']}",_json.dumps(cb),usuario)
                    if 'Ativos' in dfs:
                        dfm=calc_multimarcas(dfs['Ativos'],dfs)
                        ml=[int(x) for x in dfm[dfm['is_multimarca']]['CodigoRevendedora'].dropna().unique()]
                        _uc(f"multi_global_{ca['id']}",_json.dumps(ml),usuario)
                    # ER
                    if 'ER' in dfs:
                        df_er_f=dfs['ER'][(dfs['ER']['MeioCaptacao']=='VD+')&(dfs['ER']['SituaçãoComercial']=='Entregue')].copy()
                        st.session_state['df_er_raw']=df_er_f
                        try:
                            er_s=set(int(x) for x in df_er_f['Pessoa'].dropna().unique())
                            rev_er_t=len(er_s); rev_mu_t=0; rev_mk_t=0; rev_cb_t=0; cb_l=[]; mk_l=[]
                            if 'Ativos' in dfs:
                                dfm2=calc_multimarcas(dfs['Ativos'],dfs)
                                ms=set(int(x) for x in dfm2[dfm2['is_multimarca']]['CodigoRevendedora'].dropna().unique())
                                rev_mu_t=len(er_s&ms)
                            if 'Make' in dfs:
                                mks=set(int(x) for x in dfs['Make']['CodigoRevendedora'].dropna().unique())
                                mk_l=[int(x) for x in (er_s&mks)]; rev_mk_t=len(mk_l)
                            if 'Cabelos' in dfs:
                                cbs=set(int(x) for x in dfs['Cabelos']['CodigoRevendedora'].dropna().unique())
                                cb_l=[int(x) for x in (er_s&cbs)]; rev_cb_t=len(cb_l)
                            for k2,v2 in [(f"er_rev_total_{ca['id']}",rev_er_t),(f"er_rev_multi_{ca['id']}",rev_mu_t),(f"er_rev_make_{ca['id']}",rev_mk_t),(f"er_rev_cab_{ca['id']}",rev_cb_t),(f"er_cab_list_{ca['id']}",_json.dumps(cb_l)),(f"er_make_list_{ca['id']}",_json.dumps(mk_l))]:
                                _uc(k2,v2,usuario)
                            # Dados agregados ER
                            total_rv=df_er_f['Pessoa'].nunique()
                            df_b=df_er_f.copy(); df_b['Bairro']=df_b['Bairro'].str.upper().str.strip()
                            br=df_b.groupby('Bairro')['Pessoa'].nunique().reset_index()
                            br['pct']=round(br['Pessoa']/total_rv*100,1)
                            _uc(f"er_bairro_{ca['id']}",_json.dumps(br.rename(columns={'Pessoa':'rvs'}).sort_values('rvs',ascending=False).to_dict('records')),usuario)
                            sr=df_er_f.groupby('Papel')['Pessoa'].nunique().reset_index(); sr['pct']=round(sr['Pessoa']/total_rv*100,1)
                            tk=df_er_f.groupby('Papel').agg(rec=('ValorPraticado','sum'),rvs=('Pessoa','nunique')).reset_index()
                            tk['ticket']=round(tk['rec']/tk['rvs'],2); tk_map={r['Papel']:float(r['ticket']) for _,r in tk.iterrows()}
                            sr['ticket']=sr['Papel'].map(tk_map)
                            _uc(f"er_seg_{ca['id']}",_json.dumps(sr.rename(columns={'Papel':'seg','Pessoa':'rvs'}).sort_values('rvs',ascending=False).to_dict('records')),usuario)
                            dias_pt={0:'Segunda',1:'Terça',2:'Quarta',3:'Quinta',4:'Sexta',5:'Sábado',6:'Domingo'}
                            df_er_f['DataCap']=pd.to_datetime(df_er_f['Data Captação'],dayfirst=True,errors='coerce')
                            freq=df_er_f.groupby('DataCap')['Pessoa'].nunique().reset_index()
                            freq=freq.dropna(subset=['DataCap']).sort_values('DataCap')
                            freq['label']=freq['DataCap'].dt.strftime('%d/%m')+'('+freq['DataCap'].dt.dayofweek.map(dias_pt)+')'
                            _uc(f"er_freq_{ca['id']}",_json.dumps([{'label':r['label'],'rvs':int(r['Pessoa'])} for _,r in freq.iterrows()]),usuario)
                            if 'Cabelos' in dfs:
                                cab_set=set(int(x) for x in dfs['Cabelos'][dfs['Cabelos']['ValorPraticado']>0]['CodigoRevendedora'].dropna().unique())
                                df_er_f['is_cab']=df_er_f['Pessoa'].isin(cab_set)
                                cr=df_er_f.groupby('Usuario de Finalização').agg(total=('Pessoa','count'),n_cab=('is_cab','sum')).reset_index()
                                cr['pct_cab']=round(cr['n_cab']/cr['total']*100,1)
                                _uc(f"er_rank_cab_{ca['id']}",_json.dumps(cr.rename(columns={'Usuario de Finalização':'usuario'}).to_dict('records')),usuario)
                            if 'Make' in dfs:
                                make_set=set(int(x) for x in dfs['Make'][dfs['Make']['ValorPraticado']>0]['CodigoRevendedora'].dropna().unique())
                                df_er_f['is_mak']=df_er_f['Pessoa'].isin(make_set)
                                mr=df_er_f.groupby('Usuario de Finalização').agg(total=('Pessoa','count'),n_mak=('is_mak','sum')).reset_index()
                                mr['pct_mak']=round(mr['n_mak']/mr['total']*100,1)
                                _uc(f"er_rank_mak_{ca['id']}",_json.dumps(mr.rename(columns={'Usuario de Finalização':'usuario'}).to_dict('records')),usuario)
                        except Exception as e_er: st.warning(f"⚠️ Dados ER: {e_er}")
                    # Vendedor
                    if 'Vendedor' in dfs and 'ER' in dfs:
                        try:
                            df_v=dfs['Vendedor'].copy()
                            df_er_v=dfs['ER'][(dfs['ER']['MeioCaptacao']=='VD+')&(dfs['ER']['SituaçãoComercial']=='Entregue')].copy()
                            # Normalizar pedido para cruzamento
                            df_v['ped_norm']=df_v['Código Pedido'].astype(str).str.replace('.','',regex=False).str.strip()
                            df_er_v['ped_norm']=df_er_v['CodigoPedido'].astype(str).str.strip()
                            # Cruzar pedido → vendedor → revendedor
                            vend_map=df_v[['ped_norm','Vendedor','Código Revendedor']].drop_duplicates()
                            df_er_v=df_er_v.merge(vend_map,on='ped_norm',how='left')
                            # CPF sets para conversão
                            multi_set=set(int(x) for x in dfm[dfm['is_multimarca']]['CodigoRevendedora'].dropna().unique()) if 'Ativos' in dfs else set()
                            mak_set=set(int(x) for x in dfs['Make'][dfs['Make']['ValorPraticado']>0]['CodigoRevendedora'].dropna().unique()) if 'Make' in dfs else set()
                            cab_set=set(int(x) for x in dfs['Cabelos'][dfs['Cabelos']['ValorPraticado']>0]['CodigoRevendedora'].dropna().unique()) if 'Cabelos' in dfs else set()
                            df_er_v['is_multi']=df_er_v['Pessoa'].isin(multi_set)
                            df_er_v['is_mak']=df_er_v['Pessoa'].isin(mak_set)
                            df_er_v['is_cab']=df_er_v['Pessoa'].isin(cab_set)
                            # Por vendedor: atendidos únicos e % conversão
                            vend_conv=[]
                            for vend,grp in df_er_v.groupby('Vendedor'):
                                if pd.isna(vend): continue
                                revs=set(int(x) for x in grp['Pessoa'].dropna().unique())
                                at=len(revs)
                                pmu=len(revs&multi_set)/at*100 if at>0 else 0
                                pcb=len(revs&cab_set)/at*100 if at>0 else 0
                                pmk=len(revs&mak_set)/at*100 if at>0 else 0
                                tk_v=grp['ValorPraticado'].sum()/at if at>0 else 0
                                vend_conv.append({'vendedor':vend,'atendidos':at,'pct_multi':round(pmu,1),'pct_cab':round(pcb,1),'pct_make':round(pmk,1),'ticket':round(float(tk_v),2)})
                            _uc(f"er_vend_conv_{ca['id']}",_json.dumps(vend_conv),usuario)
                            # Mapa CPF -> nome revendedor
                            rv_nome_map={}
                            try:
                                for _,rw in df_v[["Código Revendedor","Revendedor"]].drop_duplicates().iterrows():
                                    try: rv_nome_map[int(str(rw["Código Revendedor"]).replace(".","").strip())]=str(rw["Revendedor"])
                                    except: pass
                            except: pass
                            # Não convertidos — apenas revendedores com vendedor identificado
                            nao_conv=[]
                            df_com_vend=df_er_v[df_er_v['Vendedor'].notna()]
                            for pessoa in df_com_vend['Pessoa'].dropna().unique():
                                try: cpf=int(pessoa)
                                except: continue
                                vends=list(df_com_vend[df_com_vend['Pessoa']==pessoa]['Vendedor'].dropna().unique())
                                if not vends: continue
                                rv=rv_nome_map.get(cpf,str(cpf))
                                if cpf not in cab_set: nao_conv.append({'tipo':'cab','revendedor':str(rv),'vendedores':[str(v) for v in vends]})
                                if cpf not in mak_set: nao_conv.append({'tipo':'make','revendedor':str(rv),'vendedores':[str(v) for v in vends]})
                                if cpf not in multi_set: nao_conv.append({'tipo':'multi','revendedor':str(rv),'vendedores':[str(v) for v in vends]})
                            _uc(f"er_nao_conv_{ca['id']}",_json.dumps(nao_conv,ensure_ascii=False),usuario)
                        except Exception as e_v: st.warning(f"⚠️ Dados Vendedor: {e_v}")
                    for nm in uploaded: log_upload(ca['id'],nm,usuario)
                    st.success(f"✅ {len(uploaded)} arquivo(s) processados! Ativos: {ag}")
                except Exception as e: st.error(f"❌ Erro: {e}")
    elif aba=="Usuários":
        requer_perfil("admin")
        st.markdown('<span style="color:#94a3b8;font-size:12px">Gerencie os usuários do sistema.</span>',unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
        with st.expander("➕ Novo usuário"):
            nu1,nu2,nu3=st.columns(3)
            novo_nome=nu1.text_input("Nome de usuário",key="nu_nome")
            novo_senha=nu2.text_input("Senha",type="password",key="nu_senha")
            novo_perfil=nu3.selectbox("Perfil",["consultor","gerencia","admin"],key="nu_perfil")
            if st.button("Criar usuário"):
                if novo_nome and novo_senha:
                    ex=sb.table("usuarios").select("id").eq("nome",novo_nome).execute()
                    if ex.data: st.error("Usuário já existe.")
                    else:
                        sb.table("usuarios").insert({"nome":novo_nome,"senha_hash":hash_senha(novo_senha),"perfil":novo_perfil,"ativo":True}).execute()
                        st.success(f"✅ Usuário {novo_nome} criado!"); st.rerun()
                else: st.error("Preencha nome e senha.")
        usuarios=get_usuarios()
        if usuarios:
            for u in usuarios:
                cu1,cu2,cu3,cu4,cu5=st.columns([3,2,2,2,1])
                cu1.markdown(f'<span style="color:white;font-size:13px">{u["nome"]}</span>',unsafe_allow_html=True)
                cu2.markdown(f'<span style="font-size:12px;color:#64748b">{u["perfil"]}</span>',unsafe_allow_html=True)
                cu3.markdown(f'<span style="font-size:12px;color:{"#4ade80" if u["ativo"] else "#f87171"}">{"✅ Ativo" if u["ativo"] else "❌ Inativo"}</span>',unsafe_allow_html=True)
                with cu4:
                    np=st.selectbox("",["consultor","gerencia","admin"],index=["consultor","gerencia","admin"].index(u['perfil']),key=f"up_{u['id']}",label_visibility="collapsed")
                with cu5:
                    if st.button("💾",key=f"us_{u['id']}"): sb.table("usuarios").update({"perfil":np,"ativo":True}).eq("id",u['id']).execute(); st.rerun()
                # Reset senha
                with st.expander(f"🔑 Resetar senha — {u['nome']}",expanded=False):
                    ns=st.text_input("Nova senha",type="password",key=f"ns_{u['id']}")
                    if st.button("Alterar senha",key=f"as_{u['id']}"):
                        if ns: sb.table("usuarios").update({"senha_hash":hash_senha(ns)}).eq("id",u['id']).execute(); st.success("Senha alterada!")
    elif aba=="Logs":
        tl1,tl2,tl3=st.tabs(["Uploads","Alterações","Acessos"])
        with tl1:
            ca=get_ciclo_ativo()
            if ca:
                logs=get_logs(ca['id'])
                if logs:
                    dl=pd.DataFrame(logs); dl['data_upload']=pd.to_datetime(dl['data_upload']).dt.strftime('%d/%m/%Y %H:%M')
                    st.dataframe(dl[['arquivo','usuario','data_upload']],use_container_width=True)
                else: st.info("Sem uploads.")
        with tl2:
            r=sb.table("log_alteracoes").select("*").order("created_at",desc=True).limit(50).execute()
            if r.data:
                dla=pd.DataFrame(r.data); dla['created_at']=pd.to_datetime(dla['created_at']).dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(dla[['tabela','campo','valor_anterior','valor_novo','usuario','created_at']],use_container_width=True)
        with tl3:
            try:
                ra=sb.table("log_acessos").select("*").order("created_at",desc=True).limit(100).execute()
                if ra.data:
                    dla2=pd.DataFrame(ra.data); dla2['created_at']=pd.to_datetime(dla2['created_at']).dt.strftime('%d/%m/%Y %H:%M')
                    st.dataframe(dla2[['usuario','perfil','acao','created_at']],use_container_width=True)
            except: st.info("Tabela log_acessos não encontrada.")

# =============================================
# MAIN
# =============================================
check_auth()
if not st.session_state.get("perfil"):
    login_screen()
else:
    ciclos=get_ciclos(); ciclo_ativo=get_ciclo_ativo()
    with st.sidebar:
        iniciais="".join([p[0].upper() for p in st.session_state.usuario.split()[:2]])
        st.markdown(f'<div style="padding:16px 8px 12px"><div style="font-size:15px;font-weight:700;color:white;margin-bottom:12px">💼 Venda Direta</div>'
                    f'<div style="display:flex;align-items:center;gap:10px;padding:10px;background:#111;border-radius:8px;border:1px solid #1e1e1e">'
                    f'<div style="width:32px;height:32px;border-radius:50%;background:#f59e0b;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:#000;flex-shrink:0">{iniciais}</div>'
                    f'<div><div style="font-size:12px;font-weight:600;color:white">{st.session_state.usuario}</div>'
                    f'<div style="font-size:10px;color:#475569">{st.session_state.perfil}</div></div></div></div>',unsafe_allow_html=True)
        if ciclos:
            nc=[c['nome'] for c in ciclos]; ia=next((i for i,c in enumerate(ciclos) if c['ativo']),0)
            sn=st.selectbox("Ciclo",nc,index=ia); cs=next((c for c in ciclos if c['nome']==sn),ciclo_ativo)
            st.session_state.ciclo_sel_id=cs['id'] if cs else None
        st.markdown("<hr style='border-color:#1e1e1e;margin:8px 0'>",unsafe_allow_html=True)
        MENU=[("📊 Indicadores","pg_home"),("👥 Base","pg_base"),("💼 Financeiro","pg_financeiro"),("🎯 IAF","pg_iaf"),("🏪 ER","pg_er"),("⚙️ Configurações","pg_config")]
        if 'pg_atual' not in st.session_state: st.session_state.pg_atual="📊 Indicadores"
        for label,_ in MENU:
            ativo=st.session_state.pg_atual==label
            if ativo:
                st.markdown(f'<div style="background:#2563eb;border-radius:8px;padding:9px 14px;font-size:13px;color:white;font-weight:600;margin-bottom:3px">{label}</div>',unsafe_allow_html=True)
            else:
                if st.button(label,key=f"nav_{label}",use_container_width=True):
                    st.session_state.pg_atual=label; st.rerun()
        st.markdown("<hr style='border-color:#1e1e1e;margin:8px 0'>",unsafe_allow_html=True)
        if st.button("🔄 Atualizar",use_container_width=True):
            st.cache_resource.clear(); st.rerun()
        if st.button("Sair",use_container_width=True):
            try: get_sb().table("log_acessos").insert({"usuario":st.session_state.usuario,"perfil":st.session_state.perfil,"acao":"logout"}).execute()
            except: pass
            st.session_state.perfil=None; st.session_state.usuario=None; st.rerun()
        # Data de atualização
        st.markdown("<div style='flex:1'></div>",unsafe_allow_html=True)
        ca_sb=get_ciclo_ativo()
        if ca_sb:
            logs_sb=get_logs(ca_sb['id'])
            if logs_sb:
                _dt=pd.to_datetime(logs_sb[0]['data_upload'],utc=True)
                try: ult=_dt.tz_convert('America/Sao_Paulo').strftime('%d/%m/%Y %H:%M')
                except: ult=(_dt-pd.Timedelta(hours=3)).strftime('%d/%m/%Y %H:%M')
                st.markdown(f'<div style="padding:8px;margin-top:8px"><div style="font-size:10px;color:#334155">🕐 Última atualização</div><div style="font-size:11px;color:#475569;margin-top:2px">{ult}</div></div>',unsafe_allow_html=True)
    cid=st.session_state.get('ciclo_sel_id')
    pg=st.session_state.get('pg_atual',"📊 Indicadores")
    if pg=="📊 Indicadores": pg_home(cid)
    elif pg=="👥 Base": pg_base(cid)
    elif pg=="💼 Financeiro": pg_financeiro(cid)
    elif pg=="🎯 IAF": pg_iaf(cid)
    elif pg=="🏪 ER": pg_er(cid)
    elif pg=="⚙️ Configurações": pg_config()
