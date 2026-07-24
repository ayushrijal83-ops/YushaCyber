"""Reusable simulator packages that ride on top of the labs framework.

Each subpackage exposes a Simulator subclass that plugs into the
existing lab engine (session manager, action pipeline, objective
validators, XP + achievement engines) so no new orchestration is
needed. YC-030.1 introduces app/simulators/soc/, a SOC Analyst
workspace that composes the Digital Forensics simulator so nothing
is duplicated.
"""
