# Finance tools

Every tool takes an optional `item_id`. Omit it to use the default linked item from `items.json`. A blank `item_id` is an error. An unknown `item_id` is an error.

Results are JSON objects, not sentences.

## get_accounts

Calls `/accounts/get`.

```json
{
  "itemId": "item-id",
  "accounts": [
    {
      "accountId": "account-id",
      "name": "Plaid Checking",
      "officialName": "Plaid Gold Standard 0% Interest Checking",
      "type": "depository",
      "subtype": "checking",
      "mask": "0000",
      "balances": {
        "current": 110,
        "available": 100,
        "limit": null,
        "isoCurrencyCode": "USD"
      }
    }
  ]
}
```

The ids in that example are shapes, not live account ids.

## get_transactions

Calls `/transactions/get`.

| Parameter | Purpose |
| --- | --- |
| `start_date` | Required `YYYY-MM-DD` |
| `end_date` | Required `YYYY-MM-DD` |
| `count` | Default 100. From 1 to 500 |
| `offset` | Default 0. Zero or greater |
| `item_id` | Optional |

`start_date` must be on or before `end_date`.

```json
{
  "itemId": "item-id",
  "accounts": [],
  "transactions": [
    {
      "transactionId": "transaction-id",
      "accountId": "account-id",
      "date": "2026-10-01",
      "name": "Uber",
      "merchantName": "Uber",
      "amount": 5.4,
      "pending": false,
      "category": ["Travel", "Taxi"],
      "paymentChannel": "in store"
    }
  ],
  "totalTransactions": 1
}
```

## get_liabilities

Calls `/liabilities/get`.

The result always includes `itemId`. `credit`, `mortgage`, and `student` are included only when that list is not empty.

Credit rows include `accountId`, payment fields, and `aprs`. Mortgage rows include `interestRate` and `propertyAddress` when Plaid sent them. Student rows include `loanStatus` and `repaymentPlan` when Plaid sent them.
