if intento is not None:
                            lote = intento
                            prioridad_obj = float(pri)
                            break
                    if lote is not None:
                        break

                if lote is None:
                    for r in ranges_try:
                        if capacity_used[r["RANGO_ID"]] >= r["CAPACIDAD"] - 1e-6:
                            continue
                        split_min = params.get("SPLIT_MIN_LBS_ANCHO18", 250) if rule_info.get("regla_aplicada") == "ANCHO18" else float(params.get("SPLIT_MIN_LBS_DEFAULT", 500.0))
                        if rule_info.get("regla_aplicada") == "COMBO_ANCHOS":
                            intento = intentar_lote_para_rango(work, seed_idx, r, capacity_used, params, rule_info, require_two_widths=True, split_min_lbs=split_min)
                            if intento is None:
                                intento = intentar_lote_para_rango(work, seed_idx, r, capacity_used, params, rule_info, require_two_widths=False, split_min_lbs=split_min)
                        else:
                            intento = intentar_lote_para_rango(work, seed_idx, r, capacity_used, params, rule_info, require_two_widths=False, split_min_lbs=split_min)
                        if intento is not None:
                            lote = intento
                            prioridad_obj = None
                            break

                if lote is not None:
                    sc = score_lote(lote, [], params, categoria=lote.get("CATEGORIA"), seed_row=work.loc[seed_idx])
                    if sc > best_score:
                        best_score = sc
                        best_lote = lote
                        best_pack = (seed_idx, rule_info, prioridad_obj)

            if best_lote is not None:
                seed_idx, rule_info, prioridad_obj = best_pack
                r_id = best_lote["RANGO_ID"]
                capacity_used[r_id] += best_lote["TOTAL_LOTE"]

                lote_num = f"LOTE_{lote_id_global:04d}"
                lote_id_global += 1

                anchos_lote_set = set()
                rows_info = []

                for idx_row, take_lbs, _, _ in best_lote["ROWS"]:
                    work.at[idx_row, "LBS_RESTANTES"] = float(work.at[idx_row, "LBS_RESTANTES"]) - take_lbs
                    lnk_val = work.at[idx_row, "LNK"]
                    tela_val = work.at[idx_row, "TELA.CUERPO"]
                    color_val = work.at[idx_row, "COLOR"]
                    prio_val = work.at[idx_row, "PRIORIDAD"]
                    bloque_val = work.at[idx_row, "BLOQUE"]

                    row_ws = get_row_widths(work, idx_row)
                    for w in row_ws:
                        if w:
                            anchos_lote_set.add(float(w))

                    rows_info.append({
                        "LNK": lnk_val,
                        "TELA.CUERPO": tela_val,
                        "COLOR": color_val,
                        "PRIORIDAD": prio_val,
                        "BLOQUE": bloque_val,
                        "LBS_ASIGNADAS": take_lbs,
                    })

                    detalle.append({
                        "LOTE_ID": lote_num,
                        "CATEGORIA": best_lote["CATEGORIA"],
                        "MIX": best_lote["MIX"],
                        "LNK": lnk_val,
                        "TELA.CUERPO": tela_val,
                        "COLOR": color_val,
                        "LBS_ASIGNADAS": take_lbs,
                        "REGELA_APLICADA": rule_info.get("regla_aplicada", "NONE"),
                    })

                resumen.append({
                    "LOTE_ID": lote_num,
                    "CATEGORIA": best_lote["CATEGORIA"],
                    "MIX": best_lote["MIX"],
                    "TOTAL_LBS": best_lote["TOTAL_LOTE"],
                    "MAXIMO": best_lote["MAXIMO"],
                    "NUM_ANCHOS": len(anchos_lote_set),
                    "ANCHOS_ROW": sorted(list(anchos_lote_set)),
                    "REGELA_APLICADA": rule_info.get("regla_aplicada", "NONE"),
                })
                made_any = True
            else:
                break

        data.loc[grp_idx] = work

    df_det = pd.DataFrame(detalle)
    df_res = pd.DataFrame(resumen)
    return df_det, df_res, capacity_used
