// Module 6 (advanced): authorization expressed as declarative data, evaluated by
// an engine outside the application code -- and entirely outside the model.
//
// These re-express the ownership decisions from Module 3 in Cedar. The same
// shape is expressible in OPA/Rego, OpenFGA/Zanzibar, or Oso.

// A customer may refund or apply a discount to an order they own.
permit (
    principal,
    action in [Action::"refundOrder", Action::"applyDiscount"],
    resource
)
when { resource has owner && resource.owner == principal };

// A customer may view only their own customer data (profile, orders).
permit (
    principal,
    action == Action::"viewCustomerData",
    resource
)
when { principal == resource };
