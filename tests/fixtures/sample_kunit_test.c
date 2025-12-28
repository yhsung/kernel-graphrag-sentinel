// SPDX-License-Identifier: GPL-2.0
/*
 * Sample KUnit test file for testing
 */

#include <kunit/test.h>

static void test_top_level_function_valid(struct kunit *test)
{
    int result = top_level_function(10);
    KUNIT_EXPECT_EQ(test, result, 0);
}

static void test_top_level_function_invalid(struct kunit *test)
{
    int result = top_level_function(-5);
    KUNIT_EXPECT_LT(test, result, 0);
}

static void test_standalone_function(struct kunit *test)
{
    int result = standalone_function();
    KUNIT_EXPECT_EQ(test, result, 42);
}

static void test_helper_function(struct kunit *test)
{
    int result = helper_function(5);
    KUNIT_EXPECT_EQ(test, result, 20);
}

static struct kunit_case sample_test_cases[] = {
    KUNIT_CASE(test_top_level_function_valid),
    KUNIT_CASE(test_top_level_function_invalid),
    KUNIT_CASE(test_standalone_function),
    KUNIT_CASE(test_helper_function),
    {}
};

static struct kunit_suite sample_test_suite = {
    .name = "sample_tests",
    .test_cases = sample_test_cases,
};

kunit_test_suite(sample_test_suite);

MODULE_LICENSE("GPL");
