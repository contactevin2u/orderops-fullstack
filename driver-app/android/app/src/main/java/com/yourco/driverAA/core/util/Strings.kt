package com.yourco.driverAA.core.util

fun String.ensureTrailingSlash() = if (endsWith("/")) this else "$this/"
