###############################################################################
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
###############################################################################
FROM wmoim/dim_eccodes_baseimage:jammy-2.36.0

# update image
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y wget git

# install csv2bufr
WORKDIR /tmp
COPY . /tmp/csv2bufr
RUN cd /tmp/csv2bufr && pip3 install . && cd /tmp && rm -R csv2bufr

# get latest version of csv2bufr templates and install
RUN export c2bt=`git -c 'versionsort.suffix=-' ls-remote --tags --sort='v:refname' https://github.com/World-Meteorological-Organization/csv2bufr-templates.git | tail -1 | cut -d '/' -f 3|sed 's/v//'` && \
    mkdir /opt/csv2bufr &&  \
    cd /opt/csv2bufr && \
    wget https://github.com/World-Meteorological-Organization/csv2bufr-templates/archive/refs/tags/v${c2bt}.tar.gz && \
    tar -zxf v${c2bt}.tar.gz --strip-components=1 csv2bufr-templates-${c2bt}/templates \
