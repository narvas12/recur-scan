import datetime
from collections import Counter
from statistics import mean, stdev

from recur_scan.transactions import Transaction


def get_n_transactions_same_amount(transaction: Transaction, all_transactions: list[Transaction]) -> int:
    """Get the number of transactions in all_transactions with the same amount as transaction"""
    return len([t for t in all_transactions if t.amount == transaction.amount])


def get_percent_transactions_same_amount(transaction: Transaction, all_transactions: list[Transaction]) -> float:
    """Get the percentage of transactions in all_transactions with the same amount as transaction"""
    if not all_transactions:
        return 0.0
    n_same_amount = len([t for t in all_transactions if t.amount == transaction.amount])
    return n_same_amount / len(all_transactions)


def get_time_based_recurrence_patterns(
    transaction: Transaction, all_transactions: list[Transaction]
) -> dict[str, int | float]:
    """Extracts recurrence patterns based on transaction history."""

    merchant_transactions = [t for t in all_transactions if t.name == transaction.name]

    if len(merchant_transactions) < 2:
        return {
            "is_biweekly": 0,
            "is_semimonthly": 0,  # New feature
            "is_monthly": 0,
            "is_bimonthly": 0,
            "is_quarterly": 0,
            "is_annual": 0,
            "avg_days_between_transactions": 0.0,
            "min_days_between_transactions": 0,
            "max_days_between_transactions": 0,
            "std_days_between_transactions": 0.0,
        }

    # Extract sorted transaction dates
    dates = sorted([datetime.datetime.strptime(t.date, "%Y-%m-%d") for t in merchant_transactions])
    date_diffs = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

    avg_days = mean(date_diffs)
    min_days = min(date_diffs)
    max_days = max(date_diffs)
    std_days = stdev(date_diffs) if len(date_diffs) > 1 else 0.0

    recurrence_counter = Counter(date_diffs)

    return {
        "is_biweekly": int(recurrence_counter[14] > 0),
        "is_semimonthly": int(any(d in {15, 16, 14, 17} for d in date_diffs)),  # New feature
        "is_monthly": int(any(27 <= d <= 31 for d in date_diffs)),
        "is_bimonthly": int(any(55 <= d <= 65 for d in date_diffs)),
        "is_quarterly": int(any(85 <= d <= 95 for d in date_diffs)),
        "is_annual": int(any(360 <= d <= 370 for d in date_diffs)),
        "avg_days_between_transactions": avg_days,
        "min_days_between_transactions": min_days,
        "max_days_between_transactions": max_days,
        "std_days_between_transactions": std_days,
    }


def validate_recurring_transaction(transaction: Transaction) -> bool:
    """
    Check if a transaction is valid for being marked as recurring based on vendor-specific rules.
    """
    vendor_name = transaction.name.lower()
    amount = transaction.amount

    always_recurring_vendors = {
        "netflix",
        "spotify",
        "microsoft",
        "amazon prime",
        "at&t",
        "verizon",
        "spectrum",
        "geico",
        "hugo insurance",
    }

    vendor_specific_rules = {
        "apple": lambda amt: 0.98 <= amt - int(amt) <= 0.99,
        "brigit": lambda amt: amt in {9.99, 14.99},
        "cleo ai": lambda amt: amt in {3.99, 6.99},
        "credit genie": lambda amt: amt in {3.49, 4.99},
    }

    if vendor_name in always_recurring_vendors:
        return True
    return bool(vendor_specific_rules.get(vendor_name, lambda _: True)(amount))


def get_vendor_subscription_features(transaction: Transaction) -> dict[str, int | str]:
    """
    Extract features related to vendor subscriptions.
    """
    major_subscriptions = {"netflix", "spotify", "disney+", "hulu", "amazon prime", "paramount+", "apple music"}
    telecom_or_insurance = {"at&t", "verizon", "t-mobile", "geico", "progressive", "state farm"}
    utility_vendors = {"duke energy", "con edison", "national grid", "pg&e", "water company", "gas company"}

    known_subscription_tiers = {
        "netflix": {8.99: "Basic", 15.49: "Standard", 19.99: "Premium"},
        "spotify": {9.99: "Individual", 12.99: "Duo", 15.99: "Family"},
        "disney+": {7.99: "Basic", 13.99: "Premium"},
    }

    vendor_name = transaction.name.lower()
    amount = transaction.amount

    return {
        "is_major_subscription": int(vendor_name in major_subscriptions),
        "is_telecom_or_insurance": int(vendor_name in telecom_or_insurance),
        "is_utility_bill": int(vendor_name in utility_vendors),
        "subscription_tier": known_subscription_tiers.get(vendor_name, {}).get(amount, "Unknown"),
    }


def get_additional_recurring_indicators(
    transaction: Transaction, all_transactions: list[Transaction]
) -> dict[str, int | float]:
    date_obj = datetime.datetime.strptime(transaction.date, "%Y-%m-%d")
    merchant_transactions = [t for t in all_transactions if t.name == transaction.name]

    if not merchant_transactions:
        return {
            "n_similar_transactions_last_3_months": 0,
            "n_similar_transactions_last_6_months": 0,
            "transaction_day_consistency": 0.0,
            "is_first_transaction_with_vendor": 1,
            "is_canceled_or_refunded": 0,
        }

    # Sort transactions by date
    dates = sorted([datetime.datetime.strptime(t.date, "%Y-%m-%d") for t in merchant_transactions])

    # Compute transactions in the last 3 and 6 months
    three_months_ago = date_obj - datetime.timedelta(days=90)
    six_months_ago = date_obj - datetime.timedelta(days=180)

    transactions_last_3_months = [d for d in dates if d >= three_months_ago]
    transactions_last_6_months = [d for d in dates if d >= six_months_ago]

    # Compute standard deviation in transaction days (consistency)
    transaction_days = [d.day for d in dates]
    if len(transaction_days) > 1:
        avg_day = sum(transaction_days) / len(transaction_days)
        day_std_dev = (sum((x - avg_day) ** 2 for x in transaction_days) / len(transaction_days)) ** 0.5
    else:
        day_std_dev = 0.0

    # Check if it's the first transaction with the vendor
    is_first_transaction = 1 if date_obj == dates[0] else 0

    # Check for refunds/cancellations
    refund_keywords = {"refund", "reversal", "canceled", "chargeback"}
    is_canceled_or_refunded = any(
        (transaction.amount == -t.amount and any(word in t.name.lower() for word in refund_keywords))
        for t in all_transactions
    )

    return {
        "n_similar_transactions_last_3_months": len(transactions_last_3_months),
        "n_similar_transactions_last_6_months": len(transactions_last_6_months),
        "transaction_day_consistency": day_std_dev,
        "is_first_transaction_with_vendor": is_first_transaction,
        "is_canceled_or_refunded": int(is_canceled_or_refunded),
    }


def get_day_of_week_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, int]:
    date_obj = datetime.datetime.strptime(transaction.date, "%Y-%m-%d")
    merchant_transactions = [t for t in all_transactions if t.name == transaction.name]
    dates = sorted([datetime.datetime.strptime(t.date, "%Y-%m-%d") for t in merchant_transactions])
    last_transaction_date = dates[-2] if len(dates) > 1 else None
    days_since_last = (date_obj - last_transaction_date).days if last_transaction_date else 0

    return {
        "day_of_month": date_obj.day,
        "weekday": date_obj.weekday(),  # Monday = 0, Sunday = 6
        "week_of_year": date_obj.isocalendar()[1],
        "is_weekend": int(date_obj.weekday() >= 5),  # 1 if weekend, 0 otherwise
        "days_since_last_transaction": days_since_last,
    }


def get_amount_based_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, float]:
    vendor_transactions = [t for t in all_transactions if t.name == transaction.name]

    if not vendor_transactions:
        return {
            "is_fixed_amount_recurring": 0,
            "amount_fluctuation_range": 0.0,
            "is_small_subscription": 0,
            "is_mid_sized_subscription": 0,
            "is_large_recurring_payment": 0,
        }

    amounts = [t.amount for t in vendor_transactions]
    min_amount, max_amount = min(amounts), max(amounts)

    return {
        "is_fixed_amount_recurring": int(max_amount <= min_amount * 1.02),
        "amount_fluctuation_range": max_amount - min_amount,
        "is_small_subscription": int(3.99 <= transaction.amount <= 14.99),
        "is_mid_sized_subscription": int(15 <= transaction.amount <= 49.99),
        "is_large_recurring_payment": int(transaction.amount >= 50),
    }


def get_temporal_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, float]:
    merchant_transactions = [t for t in all_transactions if t.name == transaction.name]
    dates = sorted([datetime.datetime.strptime(t.date, "%Y-%m-%d") for t in merchant_transactions])

    if len(dates) < 2:
        return {
            "time_since_first_transaction": 0,
            "transaction_frequency": 0.0,
        }

    first_transaction_date = dates[0]
    date_obj = datetime.datetime.strptime(transaction.date, "%Y-%m-%d")
    time_since_first = (date_obj - first_transaction_date).days

    total_days = (dates[-1] - dates[0]).days
    # Avoid division by zero by setting a minimum value for total_days
    transaction_frequency = 0.0 if total_days == 0 else len(dates) / (total_days / 30)

    return {
        "time_since_first_transaction": time_since_first,
        "transaction_frequency": transaction_frequency,
    }


def get_vendor_specific_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, int | str]:
    vendor_transactions = [t for t in all_transactions if t.name == transaction.name]
    vendor_popularity = len(vendor_transactions)

    vendor_categories = {
        "streaming": {"netflix", "spotify", "disney+", "hulu", "amazon prime"},
        "telecom": {"at&t", "verizon", "t-mobile"},
        "utilities": {"duke energy", "con edison", "national grid"},
    }

    vendor_category = "other"
    for category, vendors in vendor_categories.items():
        if transaction.name.lower() in vendors:
            vendor_category = category
            break

    return {
        "vendor_popularity": vendor_popularity,
        "vendor_category": vendor_category,
    }


def get_user_behavior_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, float]:
    user_transactions = [t for t in all_transactions if t.user_id == transaction.user_id]

    if not user_transactions:
        return {
            "user_avg_transaction_amount": 0.0,
            "user_total_spending": 0.0,
            "user_subscription_count": 0,
        }

    amounts = [t.amount for t in user_transactions]
    user_avg_transaction_amount = mean(amounts)
    user_total_spending = sum(amounts)

    # Count recurring subscriptions for the user
    user_subscription_count = len([
        t
        for t in user_transactions
        if t.name in {"netflix", "spotify", "disney+", "hulu", "amazon prime", "at&t", "verizon", "t-mobile"}
    ])

    return {
        "user_avg_transaction_amount": user_avg_transaction_amount,
        "user_total_spending": user_total_spending,
        "user_subscription_count": user_subscription_count,
    }


def get_refund_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, float]:
    refund_transactions = [t for t in all_transactions if t.amount == -transaction.amount]

    if not refund_transactions:
        return {
            "refund_rate": 0.0,
            "refund_time_lag": 0.0,
        }

    refund_rate = len(refund_transactions) / len(all_transactions)

    refund_time_lags = [
        (datetime.datetime.strptime(t.date, "%Y-%m-%d") - datetime.datetime.strptime(transaction.date, "%Y-%m-%d")).days
        for t in refund_transactions
    ]
    avg_refund_time_lag = mean(refund_time_lags) if refund_time_lags else 0.0

    return {
        "refund_rate": refund_rate,
        "refund_time_lag": avg_refund_time_lag,
    }


def get_features(transaction: Transaction, all_transactions: list[Transaction]) -> dict[str, float | int | str]:
    features = {
        **{
            "n_transactions_same_amount": get_n_transactions_same_amount(transaction, all_transactions),
            "percent_transactions_same_amount": get_percent_transactions_same_amount(transaction, all_transactions),
        },
        **get_time_based_recurrence_patterns(transaction, all_transactions),
        **get_vendor_subscription_features(transaction),
        **get_amount_based_features(transaction, all_transactions),
        **get_additional_recurring_indicators(transaction, all_transactions),
        **get_day_of_week_features(transaction, all_transactions),
        **get_temporal_features(transaction, all_transactions),
        **get_vendor_specific_features(transaction, all_transactions),
        **get_user_behavior_features(transaction, all_transactions),
        **get_refund_features(transaction, all_transactions),
        "is_valid_recurring_transaction": int(validate_recurring_transaction(transaction)),  # New feature
    }
    return features
