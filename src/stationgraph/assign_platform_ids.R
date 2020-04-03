library('dplyr')
library('igraph')
library("optparse")
 
option_list = list(
    make_option(c("-g","--graph"), type="character", default=NULL, 
              help="graph ml file", metavar="character"),
    make_option(c("-o","--out"), type="character", default=NULL, 
              help="output file", metavar="character")
); 
 
opt_parser = OptionParser(option_list=option_list);
opt = parse_args(opt_parser);

g <- read_graph(opt$graph,format = 'graphml')

V(g)$label[V(g)$node_type == 'Platform'] <- paste0("pid_",c(1:sum(V(g)$node_type == 'Platform')))
V(g)$name <- paste0(V(g)$station,":",V(g)$label)
el <- as_data_frame(g)

from <- rep(NA,dim(el)[1])
to <- rep(NA,dim(el)[1])
station <- rep(NA,dim(el)[1])
from_type <- rep(NA,dim(el)[1])
to_type <- rep(NA,dim(el)[1])

for(i in c(1:dim(el)[1])){
    f <- strsplit(el[i,1],":")[[1]][2]
    f_type <- unique(V(g)$node_type[V(g)$label == f])[1]
    t <- strsplit(el[i,2],":")[[1]][2]
    t_type <- unique(V(g)$node_type[V(g)$label == t])[1]

    # Train type node always in "to", street type node always in "from"
    if(f_type == 'Train' | t_type == 'Street'){
        from[i] <- t
        to[i] <- f
        from_type[i] <- t_type
        to_type[i] <- f_type
    }else{
        from[i] <- f
        to[i] <- t
        from_type[i] <- f_type
        to_type[i] <- t_type
    }
    station[i] <- strsplit(el[i,1],":")[[1]][1]
}

el_w_st <- data.frame(station_name=station,from=from,from_type=from_type,to=to,to_type=to_type,stringsAsFactors = FALSE)

el_w_st <- el_w_st[!is.na(el_w_st$station_name),]

el_w_st$to <- gsub("METRO-NORTH","METRO_NORTH",el_w_st$to)
el_from_st <- el_w_st[el_w_st$from_type == 'Street',"to"]
el_to_pl <- el_w_st[el_w_st$to_type == 'Platform',"from"]

for(i in c(1:nrow(el_w_st))){
    r = el_w_st[i,]
    if(r$to_type == 'Elevator' & r$to %in% el_from_st){
        f = r$to
        ft = r$to_type
        t = r$from
        tt = r$from_type
        el_w_st[i,c("from","from_type","to","to_type")] <- c(f,ft,t,tt)
    }else if(r$from_type == 'Elevator' & r$from %in% el_to_pl){
        f = r$to
        ft = r$to_type
        t = r$from
        tt = r$from_type
        el_w_st[i,c("from","from_type","to","to_type")] <- c(f,ft,t,tt)
    }
}

write.csv(el_w_st,file=opt$out,row.names=FALSE)