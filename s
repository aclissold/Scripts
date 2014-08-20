#!/usr/bin/env bash
#
# Instant Swift feedback. For example, 's 2 + 2' will print '$R0: Int = 4'.

echo $@ | swift
