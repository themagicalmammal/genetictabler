#!/usr/bin/env python
# coding: utf-8


import random

# The generate_courses() generates random binary strings represnting different 
# courses based on the total number of courses specified.
# IF total courses are 8 then it will generate 4 bit numbers. If 17 courses then it generates 
# 5 bit numbers but none of them will have value more than 17 or less than 1.

def generate_courses(course_count):
    bit_length = len(bin(course_count))-2
    
    n = random.randint(1, course_count)
    course = bin(n)[2:]
    course = "0" * (bit_length - len(course)) + course
    
    return course


# A function that generates the genome of specified length using generate courses function.
def generate_genome(days , slots, course_count):
    return [generate_courses(course_count) for i in range(days*slots)]


# x = generate_genome(5,2,17),
# print(x)
