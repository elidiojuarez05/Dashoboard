"""Sidebar principal de la aplicación.

Mantiene la configuración de perfil, estado de máquinas, fecha de consulta
 y cierre de sesión fuera de dashboard.py.
"""

import hashlib
import time

import streamlit as st


def render_sidebar(
    *,
    machine_configs,
    query_db,
    commit_db,
    ahora_mexico,
    cookies,
):
    """Renderiza el sidebar autenticado y devuelve la fecha seleccionada."""
    with st.sidebar:
        st.write(f"👤 Usuario: **{st.session_state.username}**")
        st.write(f"🎖️ Rol: **{st.session_state.user_role.capitalize()}**")

        with st.expander("⚙️ Editar Mi Perfil"):
            new_user_val = st.text_input(
                "Nuevo usuario",
                key="gestion_user",
                value=st.session_state.username,
            )
            new_pass_val = st.text_input(
                "Nueva Contraseña",
                type="password",
                key="gestion_pass",
                help="Dejar en blanco para no cambiar",
            )
            confirm_pass_val = st.text_input(
                "Confirmar Nueva Contraseña",
                type="password",
                key="gestion_confirm",
            )
            st.divider()
            old_pw = st.text_input(
                "Contraseña Actual",
                type="password",
                key="old_pass_input",
            )

            if st.button("💾 Guardar Cambios"):
                if old_pw:
                    res_u = query_db(
                        "SELECT * FROM usuarios WHERE username = :u",
                        {"u": st.session_state.username},
                    )
                    if (
                        not res_u.empty
                        and res_u.iloc[0]["password"]
                        == hashlib.sha256(old_pw.encode()).hexdigest()
                    ):
                        if new_pass_val == confirm_pass_val:
                            h_new = (
                                hashlib.sha256(new_pass_val.encode()).hexdigest()
                                if new_pass_val
                                else res_u.iloc[0]["password"]
                            )
                            user_id_puro = int(res_u.iloc[0]["id"])
                            exito = commit_db(
                                "UPDATE usuarios SET username = :nu, password = :np WHERE id = :uid",
                                {
                                    "nu": new_user_val,
                                    "np": h_new,
                                    "uid": user_id_puro,
                                },
                            )
                            if exito:
                                st.session_state.username = new_user_val
                                st.session_state["perfil_actualizado"] = True
                                st.rerun()
                        else:
                            st.error("❌ Contraseñas nuevas no coinciden")
                    else:
                        st.error("❌ Contraseña actual incorrecta")
                else:
                    st.warning("⚠️ Introduce tu contraseña actual para confirmar cambios")

        if st.session_state.get("perfil_actualizado"):
            st.success("✅ Contraseña y perfil actualizados correctamente")
            del st.session_state["perfil_actualizado"]

        st.divider()
        st.header("🛠️ Gestión de Equipos")
        maquina_a_configurar = st.selectbox(
            "Seleccionar Máquina para Estado:",
            list(machine_configs.keys()),
        )

        res_est_actual = query_db(
            "SELECT estado FROM estados_maquinas WHERE machine_name = :m",
            {"m": maquina_a_configurar},
        )
        est_defecto = (
            res_est_actual.iloc[0]["estado"]
            if not res_est_actual.empty
            else "Operativa"
        )
        opciones_predefinidas = [
            "Operativa",
            "Mantenimiento",
            "Falla Total",
            "Falla de Slots",
            "Falla de Tarjetas",
        ]

        if est_defecto in opciones_predefinidas:
            index_defecto = opciones_predefinidas.index(est_defecto)
            valor_personalizado_defecto = ""
        else:
            index_defecto = len(opciones_predefinidas)
            valor_personalizado_defecto = est_defecto

        opciones_select = opciones_predefinidas + ["Especificar manual"]
        nuevo_est_select = st.selectbox(
            "Definir estado:",
            opciones_select,
            index=index_defecto,
        )

        if nuevo_est_select == "Especificar manual":
            estado_final = st.text_input(
                "Ingresa la falla o estado detectado:",
                value=valor_personalizado_defecto,
            )
        else:
            estado_final = nuevo_est_select

        if st.button("🔄 Actualizar Estado"):
            if not estado_final.strip():
                st.warning("⚠️ El campo de estado personalizado no puede estar vacío.")
            elif estado_final != est_defecto:
                commit_db(
                    """
                    UPDATE historial_estados
                    SET fecha_fin = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'),
                        duracion_horas = EXTRACT(EPOCH FROM ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City') - fecha_inicio)) / 3600.0
                    WHERE machine_name = :m AND fecha_fin IS NULL
                    """,
                    {"m": maquina_a_configurar},
                )

                commit_db(
                    """
                    INSERT INTO historial_estados (machine_name, estado, fecha_inicio)
                    VALUES (:m, :e, (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'))
                    """,
                    {"m": maquina_a_configurar, "e": estado_final},
                )

                commit_db(
                    """
                    INSERT INTO estados_maquinas (machine_name, estado, updated_at)
                    VALUES (:m, :e, (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'))
                    ON CONFLICT (machine_name)
                    DO UPDATE SET estado = EXCLUDED.estado, updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City');
                    """,
                    {"m": maquina_a_configurar, "e": estado_final},
                )

                st.success(
                    f"✅ Estado de {maquina_a_configurar} guardado en la red como: **{estado_final}**"
                )
                time.sleep(1)
                st.rerun()
            else:
                st.info(f"El equipo ya se encuentra en estado: {estado_final}")

        st.divider()
        ahora_gdl = ahora_mexico()
        fecha_real_hoy = ahora_gdl.date()

        st.header("🔍 Consultar Historial")
        fecha_consulta = st.date_input(
            "Fecha de consulta",
            value=fecha_real_hoy,
            key="fecha_filtro_principal",
        )

        if st.button("Cerrar Sesión"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_role = None
            cookies["authenticated"] = "false"
            cookies["username"] = ""
            cookies["role"] = ""
            cookies.save()
            st.rerun()

    return fecha_consulta
