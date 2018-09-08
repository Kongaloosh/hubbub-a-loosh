drop table if exists subscribers;
create table entries (
  id integer primary key autoincrement,
  topic text not null,
  callback text not null,
  lease integer,
  secret text
);