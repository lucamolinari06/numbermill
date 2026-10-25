"""Saved inventor profiles and per-inventor contract views."""


def default_profiles():
    return {'grace': {'name': 'Grace', 'specialty': 'Industrial controllers',
                      'bio': 'An independent inventor who builds practical machines for local businesses.',
                      'workshop': "Grace's Workshop"}}


def roster(village):
    profiles = default_profiles()
    profiles.update(village.inventor_profiles)
    # A recorded bidder remains inspectable even before an authored profile exists.
    for offer in village.offers.values():
        key = offer.get('inventor_id')
        if key and key not in profiles:
            profiles[key] = {'name': offer.get('design_owner') or key.replace('_', ' ').title()}
    return list(profiles.items())


def contracts(village, identity):
    return [(key, offer) for key, offer in village.offers.items()
            if offer.get('inventor_id', 'grace' if offer['status'] in ('bid', 'rival') else None) == identity
            and offer['status'] in ('bid', 'rival')]


def name_for_offer(village, offer):
    identity = offer.get('inventor_id', 'grace')
    return dict(roster(village)).get(identity, {}).get('name', identity.title())
