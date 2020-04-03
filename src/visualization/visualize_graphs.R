library("igraph")
library("dplyr")
library("optparse")
 
option_list = list(
  make_option(c("-g","--graph"), type="character", default=NULL, 
              help="graph ml file", metavar="character"),
	make_option(c("--routes"), type="character", default=NULL, 
                help="routes", metavar="character"),
    make_option(c("--elevators"), type="character", default=NULL, 
                help="elevator list", metavar="character"),
    make_option(c("-o","--out"), type="character", default=NULL, 
              help="output directory", metavar="character")
); 
 
opt_parser = OptionParser(option_list=option_list);
opt = parse_args(opt_parser);

mapcolors <- function(x){
    if(x=="Elevator"){
        return("lightblue")
    }else if(x=='Street'){
        return("orange")
    }else if(x=="Platform"){
        return("white")
    }else if(grepl(pattern = "Mezzanine",x = x)){
        return("yellow")
    }else if(x=="Train"){
        return("red")
    }else {
        return("black")
    }
}

g <- read_graph(opt$graph,format = 'graphml')
routes <- read.csv(opt$routes,stringsAsFactors = F)
ee <- read.csv(opt$elevators,stringsAsFactors = F)

comp = components(g)
V(g)$component <- comp$membership

cols <- sapply(V(g)$node_type,FUN=mapcolors,simplify = TRUE)
V(g)$color <- cols
V(g)$color[V(g)$node_type=="Train"] <- paste0("#",routes$route_color[match(gsub("-.*","",V(g)$label[V(g)$node_type=="Train"]),routes$route_id)])
V(g)$color[V(g)$color == "#NA" | V(g)$color == "#"] <- 'grey'

station_components <- data.frame(component=V(g)$component,station=ee$station_name[match(V(g)$label,ee$equipment_id)],stringsAsFactors = F)
unique_stations <- unique(station_components$station)
unique_stations <- unique_stations[!is.na(unique_stations)]

write.graph(g,opt$graph,format = 'graphml')
    
if(!dir.exists(gsub("/$","",opt$out))){
    dir.create(gsub("/$","",opt$out))
}

for(x in unique_stations){
    comps <- unique(station_components$component[station_components$station == x])
    comps <- comps[!is.na(comps)]
    file_name <- gsub("_","_",gsub("[-/&_() ]+","_",x))
    png(paste0(gsub("/$","",opt$out),"/",file_name,'.png'),width = 1000,height = 1000)
    par(mfrow=c(length(comps),1))
    for(i in comps){
        h <- induced_subgraph(g,V(g)[V(g)$component == i])
            plot(h,vertex.size=8,vertex.label.degree=67.5,vertex.shape=ifelse(V(h)$node_type=='Train','square','circle'),color=V(h)$color,
                 vertex.label=gsub("-","\n",V(h)$label),vertex.label.cex=1.75,vertex.label.color='black',vertex.label.dist=-1.5,
                 layout=layout_as_tree(h,root=V(h)[V(h)$node_type == "Street"]),main=unique(ee$station_name[ee$equipment_id %in% V(h)$label]))
    }
    dev.off()
}