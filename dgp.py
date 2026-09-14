import polars as pl
import polars_stats as ps
import numpy as np
from datetime import datetime

# set up states and store ids ----
state_ids = ['OL','CA','AZ','IL','MI','IN','IN','TX','TX','FL']
timezones = ['UTC','PST','MST','CST','EST','CST','EST','MST','CST','EST']
store_ids = [9990 + i for i in range(len(state_ids))]

# date range ----
start_date = datetime(2025,11,21,8)
end_date = datetime(2025,12,3,8)
pl_ts = pl.datetime_range(start_date, end_date,"1d", eager=True).alias("trxn_date")

# interarrival times in minutes ---- 
interarrival_nrml = ps.Exponential(50.0 / 60)
interarrival_bfcm = ps.Exponential(80.0 / 60)
interarrival_nrml_ol = ps.Exponential(50.0 * 25 / 60)
interarrival_bfcm_ol = ps.Exponential(80.0 * 25 / 60)

# transaction amounts in minutes ----
amount_nrml = ps.Normal(100.,5.)
amount_bfcm = ps.Normal(120.,5.)

# approx trxn needed ---- 
n_approx = 8 * 1000

# sim data ----
df_stores = pl.DataFrame({'store_id': store_ids, 'state_id': state_ids, 'tz': timezones})
df_dates = pl.DataFrame({'trxn_dt': pl_ts})
df_sim_raw = (
  df_stores
  .join(df_dates, how='cross')
  # simulate interarrival times and purchase amounts
  .with_columns(
    ind_bfcm = pl.when( pl.col('trxn_dt').is_between(pl.date(2025,11,28),pl.date(2025,12,1)) ).then(1).otherwise(0),
    ia_nrml = pl.when( pl.col('state_id') == pl.lit('OL') )
                .then( interarrival_nrml_ol.samples(n_approx, seed=925) )
                .otherwise( interarrival_nrml.samples(n_approx, seed=925)) ,
    ia_bfcm = pl.when( pl.col('state_id') == pl.lit('OL') )
                .then( interarrival_bfcm_ol.samples(n_approx, seed=925) )
                .otherwise( interarrival_bfcm.samples(n_approx, seed=925)) ,
    ia_nrml_ol = interarrival_nrml.samples(n_approx, seed=925),
    ia_bfcm_ol = interarrival_bfcm.samples(n_approx, seed=925),  
    amount_nrml = amount_nrml.samples(n_approx, seed=925),
    amount_bfcm = amount_bfcm.samples(n_approx, seed=925),
    )
)

df_sim_clean = (
    df_sim_raw
  # cleanup and adjust which fields are used during bfcm
  .with_columns(
      pl.when(pl.col('ind_bfcm') == 1).then(pl.col('amount_bfcm')).otherwise(pl.col('amount_nrml')).alias('amount'),
      pl.when(pl.col('ind_bfcm') == 1).then(pl.col('ia_bfcm')).otherwise(pl.col('ia_nrml')).alias('interarrival'),
  )
  .select('store_id','state_id','tz','trxn_dt','amount','interarrival')
  # tidy (lengthen) and compute new timestamps 
  .explode('amount', 'interarrival')
  .with_columns(
      cum_ia_min = pl.col('interarrival').cum_sum().over(partition_by=['store_id','trxn_dt'])
  )
  .with_columns(
      trxn_ts = pl.col('trxn_dt') + pl.col('cum_ia_min') * pl.duration(minutes=1)
  )
  .filter( pl.col('trxn_ts') < pl.col('trxn_dt') + pl.duration(hours=12) )
  # switch around the timezones to UTC
  .with_columns(
      trxn_ts = pl.when(pl.col('tz') == pl.lit('UTC')).then( pl.col('trxn_ts'))
                  .when(pl.col('tz') == pl.lit('PST')).then( pl.col('trxn_ts') + pl.duration(hours=8))
                  .when(pl.col('tz') == pl.lit('MST')).then( pl.col('trxn_ts') + pl.duration(hours=7))
                  .when(pl.col('tz') == pl.lit('CST')).then( pl.col('trxn_ts') + pl.duration(hours=6))
                  .when(pl.col('tz') == pl.lit('EST')).then( pl.col('trxn_ts') + pl.duration(hours=5))
                  .otherwise(pl.col('trxn_ts'))
      )
  # date when merchandise received which tracks when data loads to table
  # for in-store this should be same day
  # for online shipping, it depends on the transaction amount (fast shipping above $100)
  .with_columns(
      ship_ts = pl.when( pl.col('state_id').is_in(['OL']) & pl.col('amount').gt(100) ).then( pl.col('trxn_ts') + pl.duration(days=2))
                  .when( pl.col('state_id').is_in(['OL']) ).then( pl.col('trxn_ts') + pl.duration(days=7))
                  .otherwise( pl.col('trxn_ts') )
  )
  # sort to hide OLs away from top 
  .sort('state_id', 'trxn_ts', descending = [True,False])
  )

# append miscellaneous columns
n = len(df_sim_clean)
rng = np.random.default_rng(seed=925)
discount = pl.Series("discount", rng.choice([0.1,0.2,0.3], size=n, p=[0.5, 0.4, 0.1]))
pay_type = pl.Series("payment_type", rng.choice(['CRD','DBT','RET','CASH'], size=n, p=[0.5, 0.4, 0.09, 0.01]))
customer_id = pl.Series("customer_id", rng.integers(10**6, 10**7, size=n ))
df_sim_final = df_sim_clean.with_columns(
    discount,
    customer_id,
    pay_type,
    amount = pl.col('amount').round(2),
    )

# final un-cleaning
# drop a single store on sunday 2025-11-30
# was it closed or is this an error? who knows? 
df_sim_final = df_sim_final.filter( ~(
  pl.col('store_id').is_in([9993]) & pl.col('trxn_ts').cast(pl.Date).eq(pl.date(2025,11,30))
) )

# prepare final dataset ----
cols_public = ['store_id','state_id','trxn_ts','ship_ts','amount','discount','payment_type','customer_id']
df_sim_final.write_csv("full.csv")
df_sim_final.filter( pl.col('ship_ts').lt(end_date) ).select(cols_public).write_csv("data.csv")