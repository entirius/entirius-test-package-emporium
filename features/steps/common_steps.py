# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Common Given steps shared across all features."""

from __future__ import annotations

from behave import given

from entirius_tests.csv_loader import (
    count_products_by_type,
    load_categories,
    load_pricelist,
    load_product_positions,
    load_products,
    load_products_by_type,
    load_quantities,
)


@given("the test package has been imported")
def step_test_package_imported(context):
    """Precondition: test package data exists in the system.

    This is a declarative precondition -- the import is done before tests run.
    The step exists so features read naturally.
    """


@given('the channel is "{channel}"')
def step_channel_is(context, channel):
    context.channel = channel


@given("the channel is the primary channel")
def step_channel_primary(context):
    context.channel = context.primary_channel


@given("the CSV products are loaded for the primary channel")
def step_load_csv_products_primary(context):
    context.csv_data = load_products(context.test_package_path, context.primary_channel)


@given("the CSV categories are loaded for the primary channel")
def step_load_csv_categories_primary(context):
    context.csv_data = load_categories(context.test_package_path, context.primary_channel)


@given("the CSV pricelist is loaded for the primary channel")
def step_load_csv_pricelist_primary(context):
    context.csv_data = load_pricelist(context.test_package_path, context.primary_channel)


@given("the CSV quantities are loaded")
def step_load_csv_quantities(context):
    context.csv_data = load_quantities(context.test_package_path)


@given('the CSV products of type "{product_type}" are loaded for the primary channel')
def step_load_csv_products_by_type(context, product_type):
    context.csv_data = load_products_by_type(context.test_package_path, context.primary_channel, product_type)


@given("the CSV product type counts are loaded for the primary channel")
def step_load_csv_product_type_counts(context):
    context.product_type_counts = count_products_by_type(context.test_package_path, context.primary_channel)


@given("the CSV product positions are loaded for the primary channel")
def step_load_csv_product_positions(context):
    context.csv_positions = load_product_positions(context.test_package_path, context.primary_channel)
