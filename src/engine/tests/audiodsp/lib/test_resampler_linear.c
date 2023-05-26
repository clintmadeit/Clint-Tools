#include <assert.h>
#include <stdio.h>

#include "audiodsp/lib/resampler_linear.h"
#include "compiler.h"
#include "./test_resampler_linear.h"

struct ResamplerStereoPair fake_generator(void* arg){
    SGFLT value = *(SGFLT*)arg;
    return (struct ResamplerStereoPair){
        .left  = value,
        .right = value,
    };
}

void TestResamplerLinearSameValue(){
    struct TestCase {
        int internal_rate;
        int target_rate;
    };
    struct TestCase test_cases[] = {
        {44100, 44100},
        {44100, 96000},
    };
    struct ResamplerLinear self;
    SGFLT value = 1.0;
    struct ResamplerStereoPair ret;
    int i, j;

    for(i = 0; i < 2; ++i){
        struct TestCase* test_case = &test_cases[i];
        resampler_linear_init(
            &self,
            test_case->internal_rate,
            test_case->target_rate,
            fake_generator
        );
        for(j = 0; j < 10; ++j){
            ret = resampler_linear_run(&self, &value);
            assert(ret.left == value);
            assert(ret.right == value);
        }
        resampler_linear_reset(&self);
    }
}

void TestResamplerLinear(){
    TestResamplerLinearSameValue();
}

