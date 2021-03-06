# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os
import time

import sqlalchemy
import sqlalchemy.ext.declarative

from sqlalchemy import asc
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import desc
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import or_
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import scoped_session

Base = sqlalchemy.ext.declarative.declarative_base()
_sessions = {}


class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True)
    dt_commit = Column(Integer)
    dt_distro = Column(Integer)
    dt_build = Column(Integer)
    project_name = Column(String(256))
    repo_dir = Column(String(1024))
    distgit_dir = Column(String(1024))
    commit_hash = Column(String(64))
    distro_hash = Column(String(64))
    commit_branch = Column(String(256))
    status = Column(String(64))
    rpms = Column(Text)
    notes = Column(Text)
    flags = Column(Integer, default=0)

    def __gt__(self, b):
        return self.dt_commit > b.dt_commit

    def __lt__(self, b):
        return self.dt_commit < b.dt_commit

    def __eq__(self, b):
        return self.dt_commit == b.dt_commit

    def getshardedcommitdir(self):
        distro_hash_suffix = ""
        if self.distro_hash:
            distro_hash_suffix = "_%s" % self.distro_hash[:8]
        return os.path.join(self.commit_hash[:2], self.commit_hash[2:4],
                            self.commit_hash + distro_hash_suffix)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    project_name = Column(String(256))
    last_email = Column(Integer)

    # Returns True if the last email sent for this project
    # was less then 24 hours ago
    def suppress_email(self):
        ct = time.time()
        if ct - self.last_email > 86400:
            return False
        return True

    def sent_email(self):
        self.last_email = int(time.time())


class CIVote(Base):
    __tablename__ = "civotes"

    id = Column(Integer, primary_key=True)
    commit_id = Column(Integer, ForeignKey('commits.id'), nullable=False)
    ci_name = Column(String(256))
    ci_url = Column(String(1024))
    ci_vote = Column(Boolean)
    ci_in_progress = Column(Boolean)
    timestamp = Column(Integer)
    notes = Column(Text)


class User(Base):
    __tablename__ = "users"

    username = Column(String(256), primary_key=True)
    password = Column(String(256), nullable=False)


# Return a db session
def getSession(url='sqlite://', new=False):
    if _sessions.get(url) and new is False:
        return _sessions.get(url)

    engine = sqlalchemy.create_engine(url)
    Base.metadata.create_all(engine)
    _sessions[url] = scoped_session(sqlalchemy.orm.sessionmaker(bind=engine))
    return _sessions[url]


# Get the most recently processed commit for project_name, we ignore commits
# with a status of "RETRY" as we want to retry these.
def getLastProcessedCommit(session, project_name, not_status="RETRY"):
    commit = session.query(Commit).filter(Commit.project_name == project_name,
                                          Commit.status != not_status).\
        order_by(desc(Commit.dt_commit)).\
        order_by(desc(Commit.id)).first()
    return commit


# Get the most recently built commit for project_name and commit_branch, we
# ignore commits with a status of "RETRY" as we want to retry these.
def getLastBuiltCommit(session, project_name, commit_branch,
                       not_status="RETRY"):
    commit = session.query(Commit).filter(Commit.project_name == project_name,
                                          Commit.status != not_status,
                                          Commit.commit_branch ==
                                          commit_branch).\
        order_by(desc(Commit.dt_build)).\
        order_by(desc(Commit.id)).first()
    return commit


def getCommits(session, project=None, with_status=None, without_status=None,
               limit=1, order="desc", since=None, before=None):
    commits = session.query(Commit)
    if project is not None:
        commits = commits.filter(Commit.project_name == project)
    if with_status is not None:
        commits = commits.filter(Commit.status == with_status)
    if without_status is not None:
        commits = commits.filter(Commit.status != without_status)
    if since is not None:
        commits = commits.filter(Commit.dt_build > since)
    if before is not None:
        commits = commits.filter(or_(Commit.dt_build is None,
                                 Commit.dt_build < before))
    order_by = desc
    if order == "asc":
        order_by = asc
    commits = commits.order_by(order_by(Commit.id))
    if limit:
        commits = commits.limit(limit)
    return commits
