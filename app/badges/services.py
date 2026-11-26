"""Dodjela bedževa.

Servisi drugih aplikacija pozivaju notify(event, users) nakon uspješne radnje. Provjera se radi
nakon commita transakcije (transaction.on_commit), pa bedž nikad ne nastaje za radnju koja nije
uspjela. Greška pri dodjeli se samo loguje: glavna radnja nikad ne pada zbog bedža.
"""
import logging

from django.db import IntegrityError, transaction

from accounts.permissions import is_club_admin, is_guide
from audit.log import audit

from .models import Badge, UserBadge
from .rules import RULES, RULES_BY_CODE

log = logging.getLogger(__name__)


def evaluate(user, events=None):
    """Provjerava pravila vezana za događaje (None = sva) i dodjeljuje nove bedževe.
    Idempotentno: postojeći bedž se ne dodjeljuje ponovo. Vraća listu novih UserBadge."""
    owned = set(UserBadge.objects.filter(user=user).values_list('badge__code', flat=True))
    rules = [r for r in RULES if r.code not in owned and (events is None or r.events & set(events))]
    if not rules:
        return []
    badges = {b.code: b for b in Badge.objects.filter(code__in=[r.code for r in rules])}
    cache, new = {}, []
    for rule in rules:
        badge = badges.get(rule.code)
        if badge is None:
            continue
        if rule.metric not in cache:
            cache[rule.metric] = rule.metric(user)
        if cache[rule.metric] < rule.goal:
            continue
        try:
            with transaction.atomic():
                ub, created = UserBadge.objects.get_or_create(user=user, badge=badge)
        except IntegrityError:       # istovremena dodjela istog bedža
            continue
        if created:
            audit(None, 'BEDZ_DODIJELJEN', 'user_badge', ub.pk, details=f'bedz={badge.code}', user=user)
            new.append(ub)
    return new


def evaluate_safely(users, events):
    for user in users:
        try:
            evaluate(user, events)
        except Exception:
            log.exception('Dodjela bedža nije uspjela (korisnik=%s, događaji=%s)', user.pk, events)


def notify(event, users):
    """Zakazuje provjeru bedževa za korisnike nakon commita. Nikad ne baca izuzetak."""
    try:
        users = [u for u in users if u is not None]
        if users:
            transaction.on_commit(lambda: evaluate_safely(users, [event]))
    except Exception:
        log.exception('Zakazivanje provjere bedževa nije uspjelo (događaj=%s)', event)


def relevant_roles(user):
    """Uloge čiji se bedževi prikazuju korisniku (i one u kojima već ima bedž)."""
    if user.is_system_admin:
        return {Badge.Role.SYSTEM}
    roles = {Badge.Role.HIKER}
    if is_guide(user):
        roles.add(Badge.Role.GUIDE)
    if is_club_admin(user):
        roles.add(Badge.Role.CLUB_ADMIN)
    roles |= set(UserBadge.objects.filter(user=user).values_list('badge__role', flat=True))
    return roles


def my_badges(user):
    """Bedževi korisnikovih uloga s napretkom do cilja. Samo za vlastiti nalog."""
    owned = {ub.badge_id: ub for ub in UserBadge.objects.filter(user=user)}
    cache, out = {}, []
    for b in Badge.objects.filter(role__in=relevant_roles(user)):
        rule = RULES_BY_CODE.get(b.code)
        ub = owned.get(b.pk)
        goal = rule.goal if rule else 1
        if ub:
            progress = goal
        elif rule:
            if rule.metric not in cache:
                cache[rule.metric] = rule.metric(user)
            progress = min(cache[rule.metric], goal)
        else:
            progress = 0
        out.append((b, ub, progress, goal))
    return out


def mark_seen(user):
    return UserBadge.objects.filter(user=user, seen=False).update(seen=True)
