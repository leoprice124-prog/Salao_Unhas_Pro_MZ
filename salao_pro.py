import streamlit as st
import sqlite3, pandas as pd, urllib.parse, hashlib, io
from datetime import datetime, date
from gtts import gTTS
import qrcode
import streamlit.components.v1 as components
components.html("""
<script>
  if (!window.parent.document.querySelector('meta[name="google-adsense-account"]')) {
    var m = window.parent.document.createElement('meta');
    m.name = 'google-adsense-account';
    m.content = 'ca-pub-6467621234967556';
    window.parent.document.head.appendChild(m);
  }
  if (!window.parent.document.querySelector('script[src*="ca-pub-6467621234967556"]')) {
    var s = window.parent.document.createElement('script');
    s.async = true;
    s.crossOrigin = 'anonymous';
    s.src = 'https://pagead2' + '://';
    window.parent.document.head.appendChild(s);
  }
</script>
""", height=0)

st.set_page_config(page_title="Studio & Salão Pro MZ — Beleza, Estética & Unhas", page_icon="💇‍♀️", layout="wide")

st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<style>
    .stButton>button { border-radius: 10px; font-weight: 600; }
    .card-fidelidade { background: linear-gradient(135deg, #2b1055, #7597de); color: white; padding: 18px; border-radius: 14px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

DB = "salao_saas_v2.db"
HASH_FORNECEDOR = hashlib.sha256(b"fracisco2003").hexdigest()

def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS saloes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, nome TEXT, cidade TEXT,
        whatsapp TEXT, mpesa_num TEXT DEFAULT '', emola_num TEXT DEFAULT '', valor_sinal REAL DEFAULT 100.0,
        meta_fidelidade INTEGER DEFAULT 5, premio_fidelidade TEXT DEFAULT '1 Serviço Bónus / Nail Art Grátis',
        senha_dono TEXT, aberto INTEGER DEFAULT 1, ativo INTEGER DEFAULT 1,
        plano TEXT DEFAULT 'Mensal', horario_funcionamento TEXT DEFAULT '08:00 às 19:00',
        aviso_texto TEXT DEFAULT '', aviso_audio BLOB, promo_video BLOB, promo_video_nome TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS profissionais (
        id INTEGER PRIMARY KEY AUTOINCREMENT, salao_id INTEGER, nome TEXT, especialidade TEXT,
        comissao_pct REAL DEFAULT 40.0, ativo INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, salao_id INTEGER, nome TEXT, categoria TEXT,
        preco REAL, duracao TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS marcacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, salao_id INTEGER, prof_id INTEGER, prof_nome TEXT,
        cliente_nome TEXT, cliente_tel TEXT, servico TEXT, valor REAL DEFAULT 0.0,
        metodo_pag TEXT DEFAULT 'No Salão', cod_transacao TEXT DEFAULT '',
        data_marc TEXT, hora_marc TEXT, status TEXT DEFAULT 'Confirmada', criado_em TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS galeria (
        id INTEGER PRIMARY KEY AUTOINCREMENT, salao_id INTEGER, titulo TEXT,
        categoria TEXT DEFAULT 'Geral', tipo TEXT, ficheiro_nome TEXT, dados BLOB, data_pub TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS stock_salao (
        id INTEGER PRIMARY KEY AUTOINCREMENT, salao_id INTEGER, item TEXT, categoria TEXT,
        qtd_atual REAL, qtd_minima REAL, unidade TEXT
    )""")
    conn.commit()

    if c.execute("SELECT COUNT(*) FROM saloes").fetchone()[0] == 0:
        c.execute("""INSERT INTO saloes (slug, nome, cidade, whatsapp, mpesa_num, emola_num, valor_sinal, senha_dono, aberto, ativo, plano, aviso_texto)
                     VALUES ('studio-vip', 'Studio & Salão Beleza Pro MZ', 'Marracuene / Maputo', '258845707294', '845707294', '879707294', 100.0, '1234', 1, 1, 'Vitalício',
                     'Bem-vinda ao nosso Salão & Estúdio! Atendimento completo em Cabelo, Tranças, Unhas de Gel, Estética e Barbearia.')""")
        sid = c.lastrowid
        profs = [
            (sid, "Ana Paula", "Manicure & Nail Designer", 40.0, 1),
            (sid, "Beatriz Mucavel", "Cabeleireira & Trancista", 45.0, 1),
            (sid, "Carla Tembe", "Esteticista & Sobrancelhas", 40.0, 1),
        ]
        c.executemany("INSERT INTO profissionais (salao_id, nome, especialidade, comissao_pct, ativo) VALUES (?,?,?,?,?)", profs)
        servs = [
            (sid, "Tranças Box Braids / Knotless", "Cabelo & Tranças", 1500.0, "3h00"),
            (sid, "Lavagem, Hidratação & Escova", "Cabelo & Tranças", 750.0, "1h30"),
            (sid, "Unhas de Gel (Aplicação)", "Unhas & Mãos", 900.0, "1h30"),
            (sid, "Manutenção de Unhas de Gel", "Unhas & Mãos", 650.0, "1h00"),
            (sid, "Pedicure Spa Completo", "Pés & Podologia", 600.0, "1h00"),
            (sid, "Design de Sobrancelhas + Henna", "Estética & Rosto", 400.0, "0h45"),
            (sid, "Maquilhagem Social / Eventos", "Maquilhagem", 1200.0, "1h30"),
        ]
        c.executemany("INSERT INTO servicos (salao_id, nome, categoria, preco, duracao) VALUES (?,?,?,?,?)", servs)
        mats = [
            (sid, "Gel Construtor UV/LED", "Unhas", 4, 2, "Potes"),
            (sid, "Pacotes de Extensão / Cabelo", "Cabelo", 12, 5, "Pacotes"),
            (sid, "Creme de Hidratação Profunda", "Cabelo", 3, 2, "Boiões"),
            (sid, "Acetona & Removedor", "Geral", 2, 2, "Litros"),
        ]
        c.executemany("INSERT INTO stock_salao (salao_id, item, categoria, qtd_atual, qtd_minima, unidade) VALUES (?,?,?,?,?,?)", mats)
        conn.commit()
    return conn

conn = get_conn()

saloes_ativos = conn.execute("SELECT id, slug, nome, cidade FROM saloes WHERE ativo=1").fetchall()
q_slug = st.query_params.get("salao", "")
slugs_disp = [s[1] for s in saloes_ativos]

with st.sidebar:
    st.markdown("### 💇‍♀️ Escolher Salão / Estúdio")
    if saloes_ativos:
        idx_def = slugs_disp.index(q_slug) if q_slug in slugs_disp else 0
        salao_sel = st.selectbox("Salão:", saloes_ativos, index=idx_def, format_func=lambda x: f"{x[2]} ({x[3]})")
    else:
        salao_sel = None
    st.divider()
    modo_acesso = st.radio("Área de Acesso:", [
        "👩 Área da Cliente (Marcar & Galeria)",
        "🔑 Painel do Dono do Salão",
        "👑 Painel do Fornecedor (SaaS)"
    ])
    st.info("📲 **Dica App:** No navegador do telemóvel, toque nos 3 pontinhos (⋮) > **Adicionar ao ecrã inicial** para instalar como App!")

if not salao_sel and modo_acesso != "👑 Painel do Fornecedor (SaaS)":
    st.warning("Nenhum salão ativo encontrado. Entre no Painel do Fornecedor para criar uma conta.")
    st.stop()

if salao_sel:
    s_id = salao_sel[0]
    s_info = conn.execute("""SELECT slug, nome, cidade, whatsapp, mpesa_num, emola_num, valor_sinal,
                             meta_fidelidade, premio_fidelidade, senha_dono, aberto, ativo, plano,
                             horario_funcionamento, aviso_texto, aviso_audio, promo_video, promo_video_nome
                             FROM saloes WHERE id=?""", (s_id,)).fetchone()
    (s_slug, s_nome, s_cid, s_wa, s_mpesa, s_emola, s_sinal, s_meta_fid, s_premio_fid,
     s_senha, s_aberto, s_ativo, s_plano, s_hor, s_aviso, s_audio, s_pvid, s_pvid_nome) = s_info

if modo_acesso == "👩 Área da Cliente (Marcar & Galeria)":
    col_t1, col_t2 = st.columns([3, 1])
    col_t1.title(f"💇‍♀️ {s_nome}")
    col_t1.caption(f"📍 {s_cid} • 🕒 Horário: {s_hor}")
    if s_aberto == 1:
        col_t2.success("🟢 SALÃO ABERTO\n\nMarcações Automáticas Ativas")
    else:
        col_t2.error("🔴 SALÃO FECHADO\n\nAgende para o próximo dia")

    if s_pvid or s_audio or s_aviso:
        with st.container(border=True):
            st.markdown("### 🎬 Cartaz Promocional & Avisos do Salão")
            cv1, cv2 = st.columns([1.4, 1])
            with cv1:
                if s_pvid:
                    st.video(s_pvid)
                elif s_aviso:
                    st.info(f"📢 **{s_aviso}**")
            with cv2:
                if s_aviso:
                    st.markdown(f"**Comunicado:** {s_aviso}")
                if s_audio:
                    st.caption("🔊 Ouvir anúncio em áudio:")
                    st.audio(s_audio, format="audio/mp3")

    aba_c1, aba_c2, aba_c3, aba_c4 = st.tabs([
        "📅 Marcar Atendimento",
        "📸 Galeria (Fotos & Vídeos)",
        "⭐ Meu Cartão Fidelidade",
        "📱 QR Code & Partilhar"
    ])

    with aba_c1:
        st.subheader("📅 Tabela de Serviços & Marcação Automática")
        servs_db = conn.execute("SELECT id, nome, categoria, preco, duracao FROM servicos WHERE salao_id=? ORDER BY categoria, nome", (s_id,)).fetchall()
        profs_db = conn.execute("SELECT id, nome, especialidade FROM profissionais WHERE salao_id=? AND ativo=1", (s_id,)).fetchall()

        if servs_db:
            cat_filtro = st.selectbox("Filtrar Categoria:", ["Todas"] + sorted(list(set(r[2] for r in servs_db))))
            df_s = pd.DataFrame(servs_db, columns=["ID", "Serviço", "Categoria", "Preço (MT)", "Duração"]).drop(columns=["ID"])
            if cat_filtro != "Todas":
                df_s = df_s[df_s["Categoria"] == cat_filtro]
            st.dataframe(df_s, use_container_width=True, hide_index=True)

        st.divider()
        c1, c2, c3 = st.columns(3)
        dt_m = c1.date_input("1. Escolha a Data:", min_value=date.today(), value=date.today())
        prof_sel = c2.selectbox("2. Escolha a Profissional:", profs_db, format_func=lambda x: f"{x[1]} ({x[2]})") if profs_db else (0, "Equipa Geral", "Salão")

        ocupadas = [r[0] for r in conn.execute("SELECT hora_marc FROM marcacoes WHERE salao_id=? AND prof_id=? AND data_marc=? AND status!='Cancelada'",
                                              (s_id, prof_sel[0], dt_m.isoformat())).fetchall()]
        todas_horas = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:30", "14:30", "15:30", "16:30", "17:30", "18:30"]
        horas_livres = [h for h in todas_horas if h not in ocupadas]

        if ocupadas:
            c3.warning(f"⏳ Ocupados com **{prof_sel[1]}**: {', '.join(ocupadas)}")
        else:
            c3.success(f"✨ Agenda livre para **{prof_sel[1]}**!")

        if not horas_livres:
            st.error(f"🚨 {prof_sel[1]} já tem a agenda cheia nesta data! Escolha outra profissional ou outro dia.")
        else:
            with st.form("form_marcacao", clear_on_submit=True):
                mc1, mc2 = st.columns(2)
                c_nome = mc1.text_input("Seu Nome Completo:*")
                c_tel = mc2.text_input("Seu WhatsApp (Ex: 841234567):*")
                mc3, mc4 = st.columns(2)
                srv_sel = mc3.selectbox("Escolha o Serviço:*", servs_db, format_func=lambda x: f"{x[1]} — {x[3]:,.0f} MT ({x[4]})") if servs_db else (0, "Atendimento Geral", "Geral", 500.0, "1h")
                c_hora = mc4.selectbox("Escolha um Horário Livre:*", horas_livres)

                st.info(f"💳 **Reserva / Sinal:** Sinal sugerido **{s_sinal:,.0f} MT** | **M-Pesa:** `{s_mpesa}` | **e-Mola:** `{s_emola}`")
                mp1, mp2 = st.columns(2)
                met_pag = mp1.selectbox("Forma de Pagamento:", ["Pagar no Salão", "Sinal Pago via M-Pesa", "Sinal Pago via e-Mola", "Total Pago via M-Pesa / e-Mola"])
                cod_tx = mp2.text_input("Código da Transação M-Pesa / e-Mola (se já pagou):", placeholder="Ex: PP261125.1842.A9182")

                if st.form_submit_button("✅ Confirmar Marcação Agora"):
                    if c_nome.strip() and c_tel.strip():
                        choque = conn.execute("SELECT 1 FROM marcacoes WHERE salao_id=? AND prof_id=? AND data_marc=? AND hora_marc=? AND status!='Cancelada'",
                                              (s_id, prof_sel[0], dt_m.isoformat(), c_hora)).fetchone()[0]
                        if choque:
                            st.error("⚠️ Esse horário acabou de ser reservado! Escolha outro horário livre.")
                        else:
                            conn.execute("""INSERT INTO marcacoes (salao_id, prof_id, prof_nome, cliente_nome, cliente_tel, servico, valor, metodo_pag, cod_transacao, data_marc, hora_marc, status, criado_em)
                                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                         (s_id, prof_sel[0], prof_sel[0], c_nome.strip(), c_tel.strip(), srv_sel[1], float(srv_sel[3]),
                                          met_pag, cod_tx.strip(), dt_m.isoformat(), c_hora, "Confirmada", datetime.now().strftime("%d/%m/%Y %H:%M")))
                            conn.commit()
                            st.success(f"🎉 Marcação confirmada com **{prof_sel[1]}** para **{dt_m.strftime('%d/%m/%Y')} às {c_hora}**!")
                            msg_wa = (f"💇‍♀️ *Nova Marcação — {s_nome}*\n👩 Cliente: {c_nome}\n🪑 Profissional: {prof_sel[1]}\n"
                                      f"✨ Serviço: {srv_sel[1]} ({srv_sel[3]:,.0f} MT)\n📅 Data: {dt_m.strftime('%d/%m/%Y')} às {c_hora}\n"
                                      f"💳 Pagamento: {met_pag} {f'(Ref: {cod_tx})' if cod_tx else ''}")
                            st.link_button("📲 Enviar Comprovativo no WhatsApp do Salão", f"https://wa.me{s_wa}?text={urllib.parse.quote(msg_wa)}")
                    else:
                        st.warning("Preencha seu nome e WhatsApp.")

        st.divider()
        st.markdown("#### 🕒 Últimas Marcações Registadas Hoje (Monitoramento Ao Vivo)")
        ultimas = pd.read_sql_query("SELECT hora_marc AS Hora, prof_nome AS Profissional, cliente_nome AS Cliente, servico AS Serviço, status AS Estado FROM marcacoes WHERE salao_id=? AND data_marc=? ORDER BY id DESC LIMIT 10",
                                     conn, params=(s_id, date.today().isoformat()))
        if not ultimas.empty:
            st.dataframe(ultimas, use_container_width=True, hide_index=True)

    with aba_c2:
        st.subheader("📸 Galeria de Trabalhos — Baixe Fotos & Vídeos")
        itens_gal = conn.execute("SELECT id, titulo, categoria, tipo, ficheiro_nome, dados, data_pub FROM galeria WHERE salao_id=? ORDER BY id DESC", (s_id,)).fetchall()
        if not itens_gal:
            st.info("Ainda não há fotos ou vídeos publicados na galeria deste salão.")
        else:
            cat_g = st.selectbox("Filtrar Galeria:", ["Todos"] + sorted(list(set(r[2] for r in itens_gal))))
            filtrados = [r for r in itens_gal if cat_g == "Todos" or r[2] == cat_g]
            cols_g = st.columns(3)
            for idx, (gid, gtit, gcat, gtipo, gfname, gdados, gdata) in enumerate(filtrados):
                with cols_g[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{gtit}**\n\n`{gcat}` • `{gdata}`")
                        if gtipo == "foto":
                            st.image(gdados, use_container_width=True)
                        else:
                            st.video(gdados)
                        st.download_button("⬇️ Baixar Foto / Vídeo", data=gdados, file_name=gfname, key=f"dl_gal_{gid}")

    with aba_c3:
        st.subheader("⭐ Consultar Meu Cartão Fidelidade")
        tel_consulta = st.text_input("Digite seu número de WhatsApp (9 dígitos):", placeholder="Ex: 841234567")
        if tel_consulta.strip():
            ult9 = "".join(filter(str.isdigit, tel_consulta))[-9:]
            qtd_vis = conn.execute("SELECT COUNT(*) FROM marcacoes WHERE salao_id=? AND cliente_tel LIKE ? AND status='Concluída'", (s_id, f"%{ult9}%")).fetchone()[0]
            progresso = qtd_vis % max(1, s_meta_fid)
            estrelas = "⭐" * progresso + "☆" * (max(1, s_meta_fid) - progresso)
            if qtd_vis > 0 and progresso == 0:
                estrelas = "⭐" * s_meta_fid
                msg_fid = f"🎉 PARABÉNS! Você completou {s_meta_fid} visitas e ganhou: **{s_premio_fid}**!"
            else:
                msg_fid = f"Você tem **{progresso}/{s_meta_fid}** visitas concluídas. Faltam **{s_meta_fid - progresso}** para ganhar: **{s_premio_fid}**!"
            st.markdown(f"""<div class="card-fidelidade"><h3>💳 Cartão Fidelidade — {s_nome}</h3><h2>{estrelas}</h2><p>{msg_fid}</p><small>Total histórico de atendimentos concluídos: {qtd_vis}</small></div>""", unsafe_allow_html=True)

    with aba_c4:
        st.subheader("📱 QR Code Oficial do Salão")
        url_base = st.text_input("Link do Portal (Altere para o link oficial do Render quando publicar):", value=f"https://onrender.com{s_slug}")
        qr_img = qrcode.make(url_base)
        buf_qr = io.BytesIO()
        qr_img.save(buf_qr, format="PNG")
        cq1, cq2 = st.columns([1, 2])
        cq1.image(buf_qr.getvalue(), caption=f"QR Code — {s_nome}", width=220)
        cq2.info("💡 **Dica de Ouro:** Imprima este QR Code e cole nos espelhos e na receção do salão para as clientes agendarem e baixarem fotos dos modelos direto no telemóvel!")
        cq2.download_button("📥 Baixar QR Code para Imprimir (PNG)", data=buf_qr.getvalue(), file_name=f"QRCode_{s_slug}.png", mime="image/png")

elif modo_acesso == "🔑 Painel do Dono do Salão":
    st.title(f"🔑 Painel de Gestão — {s_nome}")
    pw_dono = st.text_input("Senha do Dono do Salão:", type="password")
    if pw_dono != s_senha and hashlib.sha256(pw_dono.strip().lower().encode()).hexdigest() != HASH_FORNECEDOR:
        st.warning("Digite a senha do dono para gerir o salão.")
        st.stop()

    st.success(f"✅ Acesso autorizado ao painel de **{s_nome}**!")
    d_tab1, d_tab2, d_tab3, d_tab4, d_tab5 = st.tabs([
        "🟢 Status, Voz & Vídeo",
        "📅 Marcações & Caixa",
        "🪑 Equipa & Comissões",
        "📸 Galeria, Serviços & Stock",
        "🔐 Senha, M-Pesa & Fidelidade"
    ])

    with d_tab1:
        st.subheader("🟢 Abrir / Fechar Salão & Transmitir Áudio Promocional")
        est_atual = st.radio("Estado Atual do Salão:", ["🟢 Aberto (Recebendo Marcações)", "🔴 Fechado"], index=0 if s_aberto == 1 else 1, horizontal=True)
        novo_ab = 1 if "Aberto" in est_atual else 0
        txt_voz = st.text_area("✍️ Escreva o Comunicado / Promoção (O sistema converte em Áudio automaticamente):", value=s_aviso, height=110)
        vid_promo = st.file_uploader("🎬 Subir Cartaz Promocional em Vídeo com Áudio (MP4):", type=["mp4", "mov", "webm"])

        cb1, cb2 = st.columns(2)
        if cb1.button("🔊 Gerar Áudio & Publicar Tudo"):
            audio_bytes = s_audio
            if txt_voz.strip():
                tts = gTTS(text=txt_voz.strip(), lang="pt")
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                audio_bytes = fp.getvalue()
            v_bytes = vid_promo.read() if vid_promo else s_pvid
            v_name = vid_promo.name if vid_promo else s_pvid_nome
            conn.execute("UPDATE saloes SET aberto=?, aviso_texto=?, aviso_audio=?, promo_video=?, promo_video_nome=? WHERE id=?",
                         (novo_ab, txt_voz.strip(), audio_bytes, v_bytes, v_name, s_id))
            conn.commit()
            st.success("✅ Status, vídeo promocional e locução em áudio publicados!"); st.rerun()
        if cb2.button("🗑️ Limpar Vídeo / Áudio Promocional"):
            conn.execute("UPDATE saloes SET aviso_texto='', aviso_audio=NULL, promo_video=NULL WHERE id=?", (s_id,))
            conn.commit(); st.rerun()

    with d_tab2:
        st.subheader("📅 Agenda de Marcações & Caixa do Salão")
        df_m = pd.read_sql_query("""SELECT id, data_marc AS Data, hora_marc AS Hora, prof_nome AS Profissional, cliente_nome AS Cliente,
                                    cliente_tel AS WhatsApp, servico AS Serviço, valor AS Valor_MT, metodo_pag AS Pagamento,
                                    cod_transacao AS Ref_MPesa, status AS Estado FROM marcacoes WHERE salao_id=? ORDER BY data_marc DESC, hora_marc ASC""",
                                 conn, params=(s_id,))
        if not df_m.empty:
            hoje_iso = date.today().isoformat()
            fat_hoje = df_m[(df_m["Data"] == hoje_iso) & (df_m["Estado"] == "Concluída")]["Valor_MT"].sum()
            prev_hoje = df_m[(df_m["Data"] == hoje_iso) & (df_m["Estado"] != "Cancelada")]["Valor_MT"].sum()
            k1, k2, k3 = st.columns(3)
            k1.metric("💰 Caixa Concluído Hoje", f"{fat_hoje:,.2f} MT")
            k2.metric("📅 Previsão Total Hoje", f"{prev_hoje:,.2f} MT")
            k3.metric("👩 Atendimentos Hoje", len(df_m[(df_m["Data"] == hoje_iso) & (df_m["Estado"] != "Cancelada")]))

            st.dataframe(df_m, use_container_width=True, hide_index=True)
            mid_sel = st.selectbox("Selecionar Marcação:", df_m["id"].tolist(), format_func=lambda x: f"ID {x} - {df_m[df_m['id']==x]['Cliente'].values[0]} ({df_m[df_m['id']==x]['Hora'].values[0]})")
            cm_a, cm_b, cm_c = st.columns(3)
            if cm_a.button("✅ Concluir Atendimento (+1 Estrela)"):
                conn.execute("UPDATE marcacoes SET status='Concluída' WHERE id=?", (int(mid_sel),)); conn.commit(); st.rerun()
            if cm_b.button("❌ Cancelar Marcação"):
                conn.execute("UPDATE marcacoes SET status='Cancelada' WHERE id=?", (int(mid_sel),)); conn.commit(); st.rerun()
            row_m = df_m[df_m["id"] == mid_sel].iloc[0]
            tel_c = "".join(filter(str.isdigit, str(row_m["WhatsApp"])))
            if len(tel_c) == 9: tel_c = "258" + tel_c
            if tel_c:
                lemb = f"Olá {row_m['Cliente']}! 💇‍♀️ Lembramos da sua marcação no *{s_nome}* com {row_m['Profissional']} dia {row_m['Data']} às {row_m['Hora']} ({row_m['Serviço']}). Confirmado?"
                cm_c.link_button("📲 Lembrete WhatsApp", f"https://wa.me{tel_c}?text={urllib.parse.quote(lemb)}")
        else:
            st.info("Ainda não há marcações registadas.")

    with d_tab3:
        st.subheader("🪑 Equipa de Profissionais & Cálculo de Comissões")
        with st.form("add_prof", clear_on_submit=True):
            cp1, cp2, cp3 = st.columns(3)
            p_nm = cp1.text_input("Nome da Profissional:*")
            p_esp = cp2.text_input("Especialidade:*", placeholder="Ex: Manicure, Cabeleireira, Trancista, Barbeiro")
            p_com = cp3.number_input("Comissão (%):", min_value=0.0, max_value=100.0, value=40.0)
            if st.form_submit_button("➕ Adicionar Profissional") and p_nm.strip():
                conn.execute("INSERT INTO profissionais (salao_id, nome, especialidade, comissao_pct, ativo) VALUES (?,?,?,?,1)",
                             (s_id, p_nm.strip(), p_esp.strip(), p_com))
                conn.commit(); st.rerun()

        df_com = pd.read_sql_query("""SELECT p.id, p.nome AS Profissional, p.especialidade AS Especialidade, p.comissao_pct AS Comissao_Pct,
                                      COALESCE(SUM(CASE WHEN m.status='Concluída' THEN m.valor ELSE 0 END), 0) AS Total_Produzido_MT
                                      FROM profissionais p LEFT JOIN marcacoes m ON p.id=m.prof_id AND m.salao_id=p.salao_id
                                      WHERE p.salao_id=? AND p.ativo=1 GROUP BY p.id""", conn, params=(s_id,))
        if not df_com.empty:
            df_com["Valor_Comissao_MT"] = (df_com["Total_Produzido_MT"] * df_com["Comissao_Pct"] / 100.0).round(2)
            st.dataframe(df_com, use_container_width=True, hide_index=True)

    with d_tab4:
        st.subheader("📸 Galeria, Serviços & Stock de Materiais")
        sub1, sub2, sub3 = st.tabs(["🖼️ Galeria (Publicar / Apagar)", "💅 Serviços & Preços", "📦 Stock de Materiais"])
        with sub1:
            gtit = st.text_input("Título do Trabalho (Ex: Tranças Knotless, Unhas de Gel):")
            gcat = st.selectbox("Categoria:", ["Unhas & Mãos", "Cabelo & Tranças", "Pés & Podologia", "Maquilhagem & Estética", "Barbearia"])
            gfile = st.file_uploader("Foto ou Vídeo:", type=["png", "jpg", "jpeg", "mp4", "mov"])
            if st.button("📤 Publicar na Galeria") and gtit.strip() and gfile:
                gtp = "video" if gfile.name.lower().endswith(("mp4", "mov")) else "foto"
                conn.execute("INSERT INTO galeria (salao_id, titulo, categoria, tipo, ficheiro_nome, dados, data_pub) VALUES (?,?,?,?,?,?,?)",
                             (s_id, gtit.strip(), gcat, gtp, gfile.name, gfile.read(), date.today().strftime("%d/%m/%Y")))
                conn.commit(); st.success("✅ Publicado!"); st.rerun()
            df_g = pd.read_sql_query("SELECT id, titulo, categoria, tipo, data_pub FROM galeria WHERE salao_id=? ORDER BY id DESC", conn, params=(s_id,))
            if not df_g.empty:
                st.dataframe(df_g, use_container_width=True, hide_index=True)
                gid_del = st.selectbox("Apagar Item da Galeria:", df_g["id"].tolist(), format_func=lambda x: f"ID {x} - {df_g[df_g['id']==x]['titulo'].values[0]}")
                if st.button("🗑️ Remover da Galeria"):
                    conn.execute("DELETE FROM galeria WHERE id=?", (int(gid_del),)); conn.commit(); st.rerun()

        with sub2:
            sn_srv = st.text_input("Nome do Serviço:")
            sc_srv = st.selectbox("Categoria do Serviço:", ["Unhas & Mãos", "Cabelo & Tranças", "Pés & Podologia", "Maquilhagem & Estética", "Barbearia"])
            sp_srv = st.number_input("Preço (MT):", min_value=50.0, value=800.0)
            sd_srv = st.text_input("Duração:", value="1h30")
            if st.button("➕ Adicionar Serviço") and sn_srv.strip():
                conn.execute("INSERT INTO servicos (salao_id, nome, categoria, preco, duracao) VALUES (?,?,?,?,?)",
                             (s_id, sn_srv.strip(), sc_srv, sp_srv, sd_srv))
                conn.commit(); st.rerun()
            df_sv = pd.read_sql_query("SELECT id, nome, categoria, preco, duracao FROM servicos WHERE salao_id=?", conn, params=(s_id,))
            if not df_sv.empty:
                st.dataframe(df_sv, use_container_width=True, hide_index=True)
                sid_del = st.selectbox("Remover Serviço:", df_sv["id"].tolist(), format_func=lambda x: f"ID {x} - {df_sv[df_sv['id']==x]['nome'].values[0]}")
                if st.button("🗑️ Apagar Serviço"):
                    conn.execute("DELETE FROM servicos WHERE id=?", (int(sid_del),)); conn.commit(); st.rerun()

        with sub3:
            st.markdown("#### 📦 Controle de Produtos & Materiais do Salão")
            with st.form("add_stk", clear_on_submit=True):
                sk1, sk2, sk3, sk4 = st.columns(4)
                sk_it = sk1.text_input("Material (Ex: Gel UV, Extensões, Tintura):")
                sk_qt = sk2.number_input("Qtd Atual:", min_value=0.0, value=5.0)
                sk_mn = sk3.number_input("Alerta Mínimo:", min_value=0.0, value=2.0)
                sk_un = sk4.text_input("Unidade:", value="Unid/Potes")
                if st.form_submit_button("💾 Registar Material") and sk_it.strip():
                    conn.execute("INSERT INTO stock_salao (salao_id, item, categoria, qtd_atual, qtd_minima, unidade) VALUES (?,?,?,?,?,?)",
                                 (s_id, sk_it.strip(), "Geral", sk_qt, sk_mn, sk_un.strip()))
                    conn.commit(); st.rerun()
            df_stk = pd.read_sql_query("SELECT id, item AS Material, qtd_atual AS Stock_Atual, qtd_minima AS Minimo, unidade AS Unidade FROM stock_salao WHERE salao_id=?", conn, params=(s_id,))
            if not df_stk.empty:
                baixos = df_stk[df_stk["Stock_Atual"] <= df_stk["Minimo"]]
                if not baixos.empty:
                    st.error(f"⚠️ **Materiais a Acabar:** {', '.join(baixos['Material'].tolist())}")
                st.dataframe(df_stk, use_container_width=True, hide_index=True)

    with d_tab5:
        st.subheader("🔐 Alterar Senha, M-Pesa / e-Mola & Cartão Fidelidade")
        c_cfg1, c_cfg2 = st.columns(2)
        with c_cfg1:
            nn_salao = st.text_input("Nome do Salão:", value=s_nome)
            nc_salao = st.text_input("Cidade / Bairro:", value=s_cid)
            nw_salao = st.text_input("WhatsApp do Salão (258...):", value=s_wa)
            nh_salao = st.text_input("Horário:", value=s_hor)
            nova_pw = st.text_input("🔑 Nova Senha do Dono (vazio = manter):", type="password")
        with c_cfg2:
            n_mpesa = st.text_input("Número M-Pesa para Sinais:", value=s_mpesa)
            n_emola = st.text_input("Número e-Mola para Sinais:", value=s_emola)
            n_sinal = st.number_input("Valor Sugerido do Sinal (MT):", min_value=0.0, value=float(s_sinal))
            n_mfid = st.number_input("Visitas para Prémio Fidelidade:", min_value=2, max_value=20, value=int(s_meta_fid))
            n_pfid = st.text_input("Prémio do Cartão Fidelidade:", value=s_premio_fid)

        if st.button("💾 Guardar Todas as Configurações"):
            pw_final = nova_pw.strip() if len(nova_pw.strip()) >= 4 else s_senha
            conn.execute("""UPDATE saloes SET nome=?, cidade=?, whatsapp=?, horario_funcionamento=?, senha_dono=?,
                            mpesa_num=?, emola_num=?, valor_sinal=?, meta_fidelidade=?, premio_fidelidade=? WHERE id=?""",
                         (nn_salao.strip(), nc_salao.strip(), nw_salao.strip(), nh_salao.strip(), pw_final,
                          n_mpesa.strip(), n_emola.strip(), n_sinal, n_mfid, n_pfid.strip(), s_id))
            conn.commit(); st.success("✅ Configurações atualizadas!"); st.rerun()

elif modo_acesso == "👑 Painel do Fornecedor (SaaS)":
    st.title("👑 Painel Exclusivo do Fornecedor — Plataforma Multi-Salões")
    pw_f = st.text_input("Senha Mestra do Fornecedor:", type="password")
    if hashlib.sha256(pw_f.strip().lower().encode()).hexdigest() != HASH_FORNECEDOR:
        st.error("Acesso restrito ao fornecedor do software.")
        st.stop()

    st.success("👑 Bem-vindo, Leonardo! Crie contas para novos salões, barbearias e estúdios de beleza.")
    with st.form("novo_salao_form", clear_on_submit=True):
        st.markdown("#### ➕ Criar Nova Conta de Salão / Estúdio")
        fc1, fc2, fc3 = st.columns(3)
        f_nome = fc1.text_input("Nome do Salão:*", placeholder="Ex: Glamour Nails & Hair")
        f_slug = fc2.text_input("Link Único (slug):*", placeholder="Ex: glamour-nails")
        f_cid = fc3.text_input("Cidade / Bairro:", value="Maputo / Marracuene")
        fc4, fc5, fc6 = st.columns(3)
        f_wa = fc4.text_input("WhatsApp (258...):", value="25884")
        f_pw = fc5.text_input("Senha Inicial do Dono:*", value="1234")
        f_pl = fc6.selectbox("Plano:", ["Mensal (500 MT/mês)", "Trimestral (1.350 MT)", "Vitalício (3.500 MT)"])
        if st.form_submit_button("✅ Criar Conta do Salão") and f_nome.strip() and f_slug.strip():
            slug_limpo = f_slug.strip().lower().replace(" ", "-")
            conn.execute("INSERT INTO saloes (slug, nome, cidade, whatsapp, senha_dono, aberto, ativo, plano) VALUES (?,?,?,?,?,1,1,?)",
                         (slug_limpo, f_nome.strip(), f_cid.strip(), f_wa.strip(), f_pw.strip(), f_pl))
            conn.commit(); st.success(f"🎉 Conta **{f_nome}** criada! Link: `?salao={slug_limpo}`"); st.rerun()

    st.divider()
    df_saloes = pd.read_sql_query("SELECT id, slug, nome, cidade, whatsapp, senha_dono AS Senha, ativo AS Ativo, plano AS Plano FROM saloes", conn)
    st.dataframe(df_saloes, use_container_width=True, hide_index=True)
    if not df_saloes.empty:
        sid_g = st.selectbox("Gerir Conta:", df_saloes["id"].tolist(), format_func=lambda x: f"ID {x} - {df_saloes[df_saloes['id']==x]['nome'].values[0]}")
        bg1, bg2, bg3 = st.columns(3)
        if bg1.button("✅ Ativar / Renovar Mensalidade"):
            conn.execute("UPDATE saloes SET ativo=1 WHERE id=?", (int(sid_g),)); conn.commit(); st.rerun()
        if bg2.button("🔒 Bloquear por Falta de Pagamento"):
            conn.execute("UPDATE saloes SET ativo=0 WHERE id=?", (int(sid_g),)); conn.commit(); st.rerun()
        if bg3.button("🔑 Resetar Senha para 1234"):
            conn.execute("UPDATE saloes SET senha_dono='1234' WHERE id=?", (int(sid_g),)); conn.commit(); st.success("Senha redefinida para 1234!"); st.rerun()

st.divider()
with st.expander("📚 Guias de Beleza, Cuidados & Política de Privacidade (Studio & Salão Pro MZ)"):
    st.markdown("""
    ### 💅 Cuidados Essenciais com Unhas de Gel, Acrílico e Cabelo
    * **Manutenção Regular:** Para manter as unhas de gel ou acrílico saudáveis e sem infiltrações, recomenda-se a manutenção a cada 15 a 21 dias com uma profissional qualificada.
    * **Hidratação Capilar & Tranças:** Antes e depois de aplicar tranças (Box Braids, Knotless), hidrate o couro cabeludo e evite tensão excessiva nos fios.
    * **Higiene & Esterilização:** Todos os salões parceiros da plataforma seguem protocolos rigorosos de higienização de alicates, brocas e escovas.

    ---
    ### 🔒 Política de Privacidade, Cookies & Termos de Uso (Google AdSense)
    * **Sobre a Plataforma:** O **Studio & Salão Pro MZ** é um portal digital moçambicano de agendamento online, galeria de modelos e gestão para salões de beleza, estética e barbearias.
    * **Publicidade e Cookies (Google AdSense):** Este site utiliza serviços de publicidade fornecidos pelo Google (Google AdSense), que utiliza cookies para apresentar anúncios relevantes com base nas visitas anteriores dos utilizadores. Pode gerir ou desativar a publicidade personalizada nas Definições de Anúncios do Google.
    * **Contacto Oficial:** Responsável: Leonardo Jacinto Francisco • Marracuene / Maputo, Moçambique • WhatsApp: +258 84 570 7294.
    """)