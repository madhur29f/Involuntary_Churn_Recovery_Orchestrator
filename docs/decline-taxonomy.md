# Decline taxonomy

| Reason | Category | Route |
|---|---|---|
| `payment_risk_check_failed`, stolen/lost card | hard | stop |
| `card_expired`, international not allowed | customer action | card-update prompt |
| bank/gateway technical errors | soft | short retry |
| `insufficient_funds`, `card_declined` | ambiguous | model-timed retry |
| `authentication_failed` | soft | authentication prompt |
| `payment_method_not_enabled` | business error | merchant ops |

The vocabulary follows Razorpay payment-error documentation. Confirm its live list before public submission, as codes can change.
