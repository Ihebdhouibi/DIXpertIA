#!/usr/bin/env python3
"""Summarise the DMARC aggregate reports received for our domain (#186).

Why this exists
---------------
Receiving servers (Gmail first) send a daily aggregate report to the address in
our DMARC record (rua=mailto:contact@dixpertia.tn): which servers sent mail as
dixpertia.tn, how many messages, and whether each passed SPF and DKIM. Before
the policy is tightened (p=none -> quarantine -> reject), these reports must
show that all of our own mail passes, or the change sends our invitations and
invoices to spam. Read one by one they are unreadable XML in zip files; this
gives the totals.

It found, for 10-20 November 2026, that all mail passed DMARC on SPF while
DKIM failed on part of it (#261).

What it reports
---------------
- each sending server, with its message count and DMARC, DKIM and SPF results;
- per day, how many messages passed and failed DKIM;
- duplicates (the same report downloaded twice) are counted once.

The reports come from outside: an XML document with a DOCTYPE, or an archive
member over 5 MB, is refused rather than parsed.

Usage
-----
    python scripts/dmarc_report.py DIR

DIR holds the attachments as received: .zip, .gz or .xml. Keep it out of the
repository (dmarc-reports/ is ignored): the reports name the servers that sent
our mail.

Exit status 1 when any message sent as our domain failed DMARC: a server that
sends as us without passing, or an impersonation attempt.
"""

import argparse
import collections
import datetime
import gzip
import io
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_XML_BYTES = 5_000_000


def _documents(path: Path):
    """The XML documents in one attachment."""
    data = path.read_bytes()
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if member.file_size > MAX_XML_BYTES:
                    raise ValueError(f"{path.name}: {member.filename} is over {MAX_XML_BYTES} bytes")
                yield archive.read(member)
    elif data[:2] == b"\x1f\x8b":
        with gzip.open(io.BytesIO(data)) as stream:
            xml = stream.read(MAX_XML_BYTES + 1)
        if len(xml) > MAX_XML_BYTES:
            raise ValueError(f"{path.name} is over {MAX_XML_BYTES} bytes once decompressed")
        yield xml
    else:
        yield data


def _parse(xml: bytes, name: str) -> ET.Element:
    if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
        raise ValueError(f"{name}: a DOCTYPE in a DMARC report is not expected; refused")
    return ET.fromstring(xml)


def _day(timestamp: str) -> str:
    return datetime.datetime.fromtimestamp(int(timestamp), datetime.timezone.utc).strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", type=Path, help="the report attachments: .zip, .gz or .xml")
    args = parser.parse_args()

    files, seen_reports = 0, set()
    orgs, policies = collections.Counter(), collections.Counter()
    senders = collections.Counter()
    days = collections.defaultdict(lambda: [0, 0])
    for path in sorted(p for p in args.directory.iterdir() if p.is_file()):
        files += 1
        for xml in _documents(path):
            report = _parse(xml, path.name)
            report_id = report.findtext("report_metadata/report_id")
            if report_id in seen_reports:
                continue
            seen_reports.add(report_id)
            orgs[report.findtext("report_metadata/org_name")] += 1
            policies[report.findtext("policy_published/p")] += 1
            day = _day(report.findtext("report_metadata/date_range/begin"))
            for record in report.findall("record"):
                count = int(record.findtext("row/count"))
                dkim = record.findtext("row/policy_evaluated/dkim")
                spf = record.findtext("row/policy_evaluated/spf")
                passed = "pass" if "pass" in (dkim, spf) else "FAIL"
                key = (record.findtext("row/source_ip"), record.findtext("identifiers/header_from"), passed, dkim, spf)
                senders[key] += count
                days[day][0 if dkim == "pass" else 1] += count

    total = sum(senders.values())
    failed = sum(n for (_, _, passed, _, _), n in senders.items() if passed == "FAIL")
    print(f"{files} files, {len(seen_reports)} distinct reports, {total} messages")
    print(f"From: {dict(orgs)}; policy published: {dict(policies)}")
    print(f"DMARC: {total - failed} passed, {failed} failed")
    print()
    print(f"{'messages':>8}  {'source IP':<16} {'From domain':<20} DMARC  DKIM  SPF")
    for (ip, domain, passed, dkim, spf), count in senders.most_common():
        print(f"{count:>8}  {ip:<16} {domain:<20} {passed:<6} {dkim:<5} {spf}")
    print()
    print("DKIM per day (pass / fail):")
    for day, (ok, ko) in sorted(days.items()):
        print(f"  {day}  {ok:>4} / {ko}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
