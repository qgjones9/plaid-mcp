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

## get_balances

Calls `/accounts/balance/get`. This requests live balances from the institution. Use it when you need `available` or up-to-the-minute `current`. `get_accounts` stays on cached `/accounts/get`.

| Parameter | Purpose |
| --- | --- |
| `item_id` | Optional |
| `account_ids` | Optional list of Plaid account ids. Omit to refresh every account on the item. An empty list is an error. |

```json
{
  "itemId": "item-id",
  "accounts": [
    {
      "accountId": "account-id",
      "name": "360 Checking",
      "officialName": "360 Checking",
      "type": "depository",
      "subtype": "checking",
      "mask": "5261",
      "lastUpdatedDatetime": "2026-10-10T18:00:00Z",
      "balances": {
        "current": 1196.2,
        "available": 45.46,
        "limit": null,
        "isoCurrencyCode": "USD"
      }
    }
  ]
}
```

`lastUpdatedDatetime` appears only when Plaid sent `last_updated_datetime`. `available` may still be `null` when the institution does not provide it.

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
