"""Synthetic data: campaign targeted at past buyers; coupon_redeemed is recorded after purchase."""
import random

rng = random.Random(7)
with open("customers.csv", "w", encoding="utf-8", newline="\n") as fh:
    fh.write("customer_id,prior_purchases,received_campaign,coupon_redeemed,purchased\n")
    for cid in range(1, 3001):
        prior = int(rng.random() * 6)
        received = rng.random() < (0.15 + 0.14 * prior)
        purchased = rng.random() < (0.05 + 0.12 * prior)
        coupon = purchased and received and rng.random() < 0.9
        fh.write(f"{cid},{prior},{int(received)},{int(coupon)},{int(purchased)}\n")
