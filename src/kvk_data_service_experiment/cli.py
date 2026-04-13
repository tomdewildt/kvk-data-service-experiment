import argparse
import json
from pathlib import Path
from pprint import pprint

from loguru import logger

from kvk_data_service_experiment.client import create_kvk_client
from kvk_data_service_experiment.config import config
from kvk_data_service_experiment.exceptions import UnknownCommandError
from kvk_data_service_experiment.service import KVKDataService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the KVK Data Service SOAP API")
    parser.add_argument("--output", metavar="FILE", help="Write result to a JSON file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Registration
    registration_parser = subparsers.add_parser("registration", help="Fetch business registration")
    registration_parser_group = registration_parser.add_mutually_exclusive_group(required=True)
    registration_parser_group.add_argument("--kvk-number", metavar="NUMBER", help="KvK number (8 digits)")
    registration_parser_group.add_argument("--rsin", metavar="NUMBER", help="RSIN number (9 digits)")

    # Branch
    branch_parser = subparsers.add_parser("branch", help="Fetch establishment/branch details")
    branch_group = branch_parser.add_mutually_exclusive_group(required=True)
    branch_group.add_argument("--branch-number", metavar="NUMBER", help="Branch number (12 digits)")
    branch_group.add_argument("--kvk-number", metavar="NUMBER", help="KvK number (8 digits)")
    branch_group.add_argument("--rsin", metavar="NUMBER", help="RSIN number (9 digits)")

    # Financial years
    financial_years_parser = subparsers.add_parser("financial-years", help="List available financial years")
    financial_years_parser.add_argument("--kvk-number", metavar="NUMBER", required=True, help="KvK number (8 digits)")

    # Financial statement
    financial_statement_parser = subparsers.add_parser("financial-statement", help="Fetch financial statement")
    financial_statement_parser.add_argument(
        "--depot-id",
        metavar="ID",
        required=True,
        help="Depot ID (from financial-years)",
    )

    # UBO
    ubo_parser = subparsers.add_parser("ubo", help="Fetch UBO register extract")
    ubo_parser.add_argument("--kvk-number", metavar="NUMBER", required=True, help="KvK number (8 digits)")

    # Extract
    extract_parser = subparsers.add_parser("extract", help="Fetch business register extract")
    extract_parser_group = extract_parser.add_mutually_exclusive_group(required=True)
    extract_parser_group.add_argument("--kvk-number", metavar="NUMBER", help="KvK number (8 digits)")
    extract_parser_group.add_argument("--rsin", metavar="NUMBER", help="RSIN number (9 digits)")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    client = create_kvk_client(config)
    service = KVKDataService(client)

    match args.command:
        case "registration":
            result = service.get_registration(kvk_number=args.kvk_number, rsin=args.rsin)
        case "branch":
            result = service.get_branch(branch_number=args.branch_number, kvk_number=args.kvk_number, rsin=args.rsin)
        case "financial-years":
            result = service.get_financial_years(kvk_number=args.kvk_number)
        case "financial-statement":
            result = service.get_financial_statement(depot_id=args.depot_id)
        case "ubo":
            result = service.get_ubo(kvk_number=args.kvk_number)
        case "extract":
            result = service.get_extract(kvk_number=args.kvk_number, rsin=args.rsin)
        case _:
            raise UnknownCommandError(args.command)

    output = json.dumps(result, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(output)
        logger.info("Result written to '{}'", args.output)
    else:
        pprint(output)


if __name__ == "__main__":
    main()
