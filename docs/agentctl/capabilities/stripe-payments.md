<!-- agentctl:auto-generated -->
# Stripe payments

- Key: `stripe-payments`
- Group: `integrations`
- Status: `missing`
- Front door: `$stripe-capability`

## Summary

Use for payment flows, subscriptions, Connect/platform work, and Stripe integration reviews.

## Navigation Skills

- `stripe-capability`

## Entry Points

- `$stripe-capability`
- `agentctl capability stripe-payments`
- `$stripe:stripe-best-practices`
- `$stripe:upgrade-stripe`

## Routing Notes

- Prefer the Stripe plugin skills for guided Stripe decisions and upgrade work.
- Use the capability page to see whether plugin coverage is enough before dropping into lower-level tooling.

## Backing Interfaces

- `skill` `stripe-capability` [ok]
- `mcp` `stripe` [missing] (configured=false)
- `plugin` `stripe@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Prefer the Stripe plugin capability surface; keep MCP as backing metadata, not a separate menu.
