"""Construye la tabla lista para el modelo: una fila por condado-año t con variables de t y ventanas,
y la clase de riesgo del año t+1. Uso: preparar_datos.py <carpeta_zip> <salida_csv>"""
import sys, numpy as np, pandas as pd
D, SALIDA = sys.argv[1], sys.argv[2]
crudo = pd.read_csv(f'{D}/county_year_climate_flood_risk.csv', dtype={'county_fips': str})
f = crudo.county_fips
base = crudo[(~f.str.endswith('000')) & (f.str[:2].astype(int) <= 56) & (crudo.year <= 2025)].copy()
base['nfip_paid_loss_usd'] = base.nfip_paid_loss_usd.clip(lower=0)
cols = ['nfip_claim_count', 'nfip_paid_loss_usd', 'high_severity_claim_count', 'storm_event_count',
        'flood_related_event_count', 'storm_total_damage_usd', 'storm_deaths', 'fema_declaration_count']
idx = pd.MultiIndex.from_product([base.county_fips.unique(), range(2000, 2026)], names=['county_fips', 'year'])
t = base.set_index(['county_fips', 'year'])[cols].reindex(idx).fillna(0).reset_index().sort_values(['county_fips', 'year'])
g = t.groupby('county_fips')
def ventana(col, n):
    return g[col].transform(lambda s: s.rolling(n, min_periods=1).sum())
out = pd.DataFrame({'county_fips': t.county_fips, 'year': t.year, 'state_fips': t.county_fips.str[:2]})
out['claims_1y'] = t.nfip_claim_count
out['claims_5y'] = ventana('nfip_claim_count', 5)
out['claims_10y'] = ventana('nfip_claim_count', 10)
out['paid_loss_5y_log'] = np.log1p(ventana('nfip_paid_loss_usd', 5))
out['severe_claims_5y'] = ventana('high_severity_claim_count', 5)
out['flood_events_1y'] = t.flood_related_event_count
out['flood_events_5y'] = ventana('flood_related_event_count', 5)
out['flood_events_10y'] = ventana('flood_related_event_count', 10)
out['storm_events_1y'] = t.storm_event_count
out['storm_damage_10y_log'] = np.log1p(ventana('storm_total_damage_usd', 10))
out['storm_deaths_10y'] = ventana('storm_deaths', 10)
out['fema_decl_5y'] = ventana('fema_declaration_count', 5)
siguiente = g.nfip_claim_count.shift(-1)
out['claims_next_year'] = siguiente
out['risk_class'] = np.select([siguiente == 0, siguiente < 10], ['bajo', 'medio'], 'alto')
out = out[siguiente.notna()].reset_index(drop=True)
out.to_csv(SALIDA, index=False)
print('Tabla procesada:', out.shape, '| años', out.year.min(), '-', out.year.max(), '| condados', out.county_fips.nunique())
