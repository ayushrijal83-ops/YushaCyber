"""Lab engine core.

Lab-type-agnostic machinery shared by every simulator. Nothing in this
package knows what "Linux" is — lab-specific behaviour lives in simulator
plugins (``app/labs/simulators/``) and in seeded database rows.

Extension points:
    * Add a simulator  -> subclass Simulator, register in the registry.
    * Add a validator  -> register a function in VALIDATOR_REGISTRY.
Neither requires changes to routes, services, or this package.
"""
