/*
 * Sample kernel-style C code for testing
 * Mimics Linux kernel patterns
 */

#include <linux/kernel.h>
#include <linux/module.h>

/* Function declarations */
static int helper_function(int value);
static void cleanup_resource(void *data);

/**
 * top_level_function - Entry point function
 * @param: Input parameter
 *
 * Returns: 0 on success, negative error code on failure
 */
int top_level_function(int param)
{
    int result;

    if (param < 0)
        return -EINVAL;

    result = helper_function(param);
    if (result < 0)
        goto error;

    return 0;

error:
    cleanup_resource(NULL);
    return result;
}

/**
 * helper_function - Helper that does computation
 * @value: Input value
 *
 * Returns: Computed result
 */
static int helper_function(int value)
{
    int intermediate;

    intermediate = value * 2;
    return intermediate + 10;
}

/**
 * cleanup_resource - Cleanup function
 * @data: Resource to clean up
 */
static void cleanup_resource(void *data)
{
    if (data)
        kfree(data);
}

/**
 * standalone_function - Function with no dependencies
 *
 * Returns: Always returns 42
 */
int standalone_function(void)
{
    return 42;
}

/**
 * multi_caller - Function that calls multiple helpers
 */
void multi_caller(void)
{
    helper_function(5);
    standalone_function();
    cleanup_resource(NULL);
}

/* Exported symbols */
EXPORT_SYMBOL(top_level_function);
EXPORT_SYMBOL(standalone_function);
