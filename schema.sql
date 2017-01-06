drop table if exists quiz;

create table quiz (
  id integer primary key autoincrement,
  'question' text not null,
  'answer' text not null
);
