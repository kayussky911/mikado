import sys,os.path
from loci_objects.excluded_locus import excluded_locus
#from loci_objects.monosublocus_holder import monosublocus_holder
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from loci_objects.abstractlocus import abstractlocus
#import random
from loci_objects.monosublocus import monosublocus
from loci_objects.transcript import transcript
from loci_objects.GFF import gffLine
from loci_objects.get_metrics_name import get_metrics_name

class sublocus(abstractlocus):
    
    '''
    The sublocus class is created either by the superlocus class during the subloci definition, or directly using a G(T|F)line-like object.
    It is used to define the final monosubloci.
    '''
    
    @staticmethod
    def get_available_metrics(filename=None):
        '''Wrapper for the "get_metrics_name" function to retrieve the necessary metrics names.'''
        
        return get_metrics_name(filename=filename)
    
    
    __name__ = "sublocus"
    available_metrics = []
    if available_metrics == []:
        available_metrics = get_available_metrics.__func__()

    ################ Class special methods ##############
    
    def __init__(self, span, source=None, json_dict = None, purge = False ):
        
        '''This class takes as input a "span" feature - e.g. a gffLine or a transcript_instance. 
        The span instance should therefore have such attributes as chrom, strand, start, end, attributes. '''
        super().__init__()
        self.fixedSize=True if span.feature=="sublocus" else False
        if span.__name__=="transcript":
            span.finalize()
        self.purge = purge

        if source is not None:
            self.source = source
        else:
            self.source = "locus_pipeline"
            
        self.excluded=None
        self.splitted=False
        self.metrics_calculated=False #Flag to indicate that we have not calculated the metrics for the transcripts
        setattr( self, "monoexonic", getattr(span, "monoexonic", None)  )
        if json_dict is None or type(json_dict) is not dict:
            raise ValueError("I am missing the configuration for prioritizing transcripts!")
        self.json_dict = json_dict
        
        #This part is necessary to import modules
        if "modules" in self.json_dict:
            import importlib
            for mod in self.json_dict["modules"]:
                globals()[mod]=importlib.import_module(mod)
        
        if type(span) is transcript:
            self.add_transcript_to_locus(span)
        else:
            for key in ["parent", "start", "end", "chrom", "strand", "attributes"]:
                setattr(self, key, getattr(span, key))
        
    def __str__(self, print_cds=True):
        
        lines=[]
        
        self_line=gffLine('')
        self.feature=self.__name__
        for attr in ["chrom", 'feature','source','start','end','strand']:
            setattr(self_line,attr, getattr(self,attr))
        self_line.phase,self_line.score=None,None
        self_line.id="{0}_{1}".format(self.source,self.id)
        self_line.name=self.name
        self_line.parent=self.parent
        self_line.attributes["multiexonic"]=(not self.monoexonic)
        lines.append(str(self_line))
    
        for tid in sorted(self.transcripts, key=lambda tid: self.transcripts[tid]):
            self.transcripts[tid].source=self.source
            self.transcripts[tid].parent=self_line.id
            lines.append(self.transcripts[tid].__str__(print_cds=print_cds).rstrip())
        
        return "\n".join(lines)

    
    ########### Class instance methods #####################
    
    def add_transcript_to_locus(self, transcript_instance):
        
        '''This is an override of the original method, as at the sublocus stage we need to accomplish a couple of things more:
        - check that transcripts added to the sublocus are either all monoexonic or all multiexonic
        - change the id of the transcripts to  
        '''
        
        if transcript_instance is None: return
        if self.initialized is False:
            self.monoexonic = transcript_instance.monoexonic
        elif self.monoexonic!=transcript_instance.monoexonic:
            raise ValueError("Sublocus and transcript are not compatible!\n{0}\t{1}\t{2}\t{3}\t{4}\n{5}".format(self.chrom,
                                                                                                           self.start,
                                                                                                           self.end,
                                                                                                           self.strand,
                                                                                                           self.monoexonic,
                                                                                                           transcript))

        super().add_transcript_to_locus(transcript_instance)
        
        #Update the id

    def define_monosubloci(self, purge=False, excluded=None):
        '''This function retrieves the best non-overlapping transcripts inside the sublocus, according to the score
        calculated by calculate_scores (explicitly called inside the method).
        The "excluded" keyword must contain either None or a monosublocus_holder object. It is used to contain
        transcripts that must be excluded from the locus due to unmet requirements. 
        '''
        
        self.monosubloci=[]
#         if type(excluded) is not excluded_locus or excluded is not None:
#             raise TypeError("Unmanageable type for the container of excluded transcripts! Type: {0}".format(type(excluded)))
        self.excluded = excluded
        self.calculate_scores()
        remaining = self.transcripts.copy()
        
        while len(remaining)>0:
            selected_tid=self.choose_best(remaining.copy())
            selected_transcript = remaining[selected_tid]
            new_remaining = remaining.copy()
            del new_remaining[selected_tid]
            for tid in filter(lambda t: t!=selected_tid, remaining.keys()):
                res=self.is_intersecting(selected_transcript, new_remaining[tid])
                if res is True:
                    del new_remaining[tid]
            if selected_transcript.score==0 and purge is True:
                pass
            else:
                new_locus = monosublocus(selected_transcript)
                self.monosubloci.append(new_locus)
            remaining=new_remaining.copy()
            if len(remaining)==0: break
            
        self.splitted=True
        return
    
   
    def calculate_metrics(self, tid):
        '''This function will calculate the metrics for a transcript which are relative in nature
        i.e. that depend on the other transcripts in the sublocus. Examples include the fraction
        of introns or exons in the sublocus, or the number/fraction of retained introns.  
        '''
    
        transcript_instance = self.transcripts[tid]
        self.transcripts[tid].finalize() # The transcript must be finalized before we can calculate the score.
        
        self.transcripts[tid].exon_fraction = len(set.intersection( self.exons,self.transcripts[tid].exons   ))/len(self.exons)

        if len(self.introns)>0:
            transcript_instance.intron_fraction = len(set.intersection(transcript_instance.introns, self.introns))/len(self.introns)
        else: 
            transcript_instance.intron_fraction = 0
        if len(self.selected_cds_introns)>0:
            transcript_instance.selected_cds_intron_fraction = len(set.intersection(transcript_instance.selected_cds_introns, set(self.selected_cds_introns)) )/len(self.selected_cds_introns)
        else:
            transcript_instance.selected_cds_intron_fraction = 0
            
        if len(self.combined_cds_introns)>0:
            transcript_instance.combined_cds_intron_fraction = len(set.intersection(set(transcript_instance.combined_cds_introns), set(self.combined_cds_introns)) )/len(self.combined_cds_introns)
        else:
            transcript_instance.combined_cds_intron_fraction = 0
            
        self.find_retained_introns(transcript_instance)
        transcript_instance.retained_fraction=sum(e[1]-e[0]+1 for e in transcript_instance.retained_introns)/transcript_instance.cdna_length
        self.transcripts[tid]=transcript_instance
        
    def find_retained_introns(self, transcript_instance):
         
        '''This method checks the number of exons that are possibly retained introns for a given transcript.
        To perform this operation, it checks for each non-CDS exon whether it exists a sublocus intron that
        is *completely* contained within a transcript exon. Such non-CDS exons must be *after* the
        CDS start; a retained intron should contain a premature stop codon, not a delayed start. 
        CDS exons are ignored because their retention might be perfectly valid.
        The results are stored inside the transcript instance, in the "retained_introns" tuple.'''
         
        transcript_instance.retained_introns=[]
        
        if transcript_instance.strand=="+":
            filtering = filter(lambda e: e not in transcript_instance.non_overlapping_cds and e[0]>=transcript_instance.combined_cds_start,
                               transcript_instance.exons                               
                               )
        else:
            filtering = filter(lambda e: e not in transcript_instance.non_overlapping_cds and e[1]<=transcript_instance.combined_cds_start,
                               transcript_instance.exons                               
                               )
        for exon in filtering:
            #Check that the overlap is at least as long as the minimum between the exon and the intron.
            if any(filter(
                          lambda junction: self.overlap(exon,junction)>=junction[1]-junction[0],
                          self.introns                          
                          )) is True:
                    transcript_instance.retained_introns.append(exon)
        transcript_instance.retained_introns=tuple(transcript_instance.retained_introns)
            
    def load_scores(self, scores):
        '''Simple mock function to load scores for the transcripts from an external dictionary.
        '''
        
        for tid in self.transcripts:
            if tid in scores:
                self.transcripts[tid].score=scores[tid]
            else:
                self.transcripts[tid].score=0            
            
    def calculate_scores(self):
        '''
        Function to calculate a score for each transcript, given the metrics derived
        with the calculate_metrics method and the scoring scheme provided in the JSON configuration.
        If any requirements have been specified, all transcripts which do not pass them
        will be assigned a score of 0 and subsequently ignored.
        Scores are rounded to the nearest integer.
        '''
        
        self.get_metrics()
        
        if "requirements" in self.json_dict:
            self.json_dict["requirements"]["compiled"]=compile(self.json_dict["requirements"]["expression"], "<json>", "eval")
            previous_not_passing = set()
            while True:
                not_passing = set()
                for tid in filter(lambda t: t not in previous_not_passing,  self.transcripts):
                    evaluated=dict()
                    for key in self.json_dict["requirements"]["parameters"]:
                        value=getattr(self.transcripts[tid],self.json_dict["requirements"]["parameters"][key]["name"])
                        evaluated[key]=self.evaluate(value, self.json_dict["requirements"]["parameters"][key])
                    if eval(self.json_dict["requirements"]["compiled"]) is False:
                        not_passing.add(tid)
                if len(not_passing)==0:
                    break
                
                for tid in not_passing:
                    self.transcripts[tid].score=0
                    if self.purge is True:
                        self.metrics_calculated=False
                        if self.excluded is None:
                            excluded = monosublocus(self.transcripts[tid])
                            self.excluded = excluded_locus(excluded)
                        else:
                            self.excluded.add_transcript_to_locus(self.transcripts[tid])
                        self.remove_transcript_from_locus(tid)
                if len(self.transcripts)==0:
                    return
                else:
                    #Recalculate the metrics
                    self.get_metrics()
                
                previous_not_passing = not_passing.copy()
                    
        if len(self.transcripts)==0:
            return
        scores=dict()
        for tid in self.transcripts:
            scores[tid]=dict()
        for param in self.json_dict["parameters"]:
            rescaling = self.json_dict["parameters"][param]["rescaling"]
            metrics = [getattr( self.transcripts[tid], param  ) for tid in self.transcripts]
            if rescaling=="target":
                target = self.json_dict["parameters"][param]["value"]
                denominator = max( abs( x-target ) for x in metrics)
            else:
                denominator=(max(metrics)-min(metrics))
            if denominator==0: denominator=1
                
            for tid in self.transcripts:
                tid_metric = getattr( self.transcripts[tid], param  )
                if rescaling == "max":
                    ##scoreAM = (rAM - min(rM))/(max(rM)-min(rM)) 
                    score = abs( ( tid_metric - min(metrics) ) / denominator )
                elif rescaling=="min":
                    score = abs( 1- ( tid_metric - min(metrics) ) / denominator )
                elif rescaling == "target":
                    score = 1 - (abs( tid_metric  - target )/denominator )
                score*=self.json_dict["parameters"][param]["multiplier"]
                scores[tid][param]=score
                
        for tid in self.transcripts:
            self.transcripts[tid].score = sum( scores[tid].values() )
        
    
    def print_metrics(self):
        
        '''This class yields dictionary "rows" that will be given to a csv.DictWriter class.'''
        
        #Check that rower is an instance of the csv.DictWriter class
        self.get_metrics()
        self.calculate_scores() 
        
        #The rower is an instance of the DictWriter class from the standard CSV module
        
        for tid in sorted(self.transcripts.keys(), key=lambda tid: self.transcripts[tid] ):
            row={}
            for key in self.available_metrics:
                if key.lower() in ("id", "tid"):
                    row[key]=tid
                elif key.lower()=="parent":
                    row[key]=self.id
                else:
                    row[key]=getattr(self.transcripts[tid], key, "NA")
                if type(row[key]) is float:
                    row[key] = round(row[key],2)
                elif row[key] is None or row[key]=="":
                    row[key]="NA"
            yield row
        if self.excluded is not None:
            for row in self.excluded.print_metrics():
                yield row
            
        return
    
    def get_metrics(self):
        
        '''Quick wrapper to calculate the metrics for all the transcripts.'''
        
        if self.metrics_calculated is True:
            return
        
        
        for tid in self.transcripts:
            self.calculate_metrics(tid)
            
        self.metrics_calculated = True
        return


    ############### Class methods ################

    @classmethod
    def is_intersecting(cls, transcript, other):
        '''
        Implementation of the is_intersecting method. Here at the level of the sublocus,
        the intersection is seen as overlap between exons. 
        '''
          
        if transcript.id==other.id: return False # We do not want intersection with oneself
        for exon in transcript.exons:
            if any(
                   filter(
                          #Check that at least one couple of exons are overlapping
                          lambda oexon: cls.overlap( exon, oexon )>=0, 
                          other.exons
                          )
                   ) is True:
                return True
        
        return False
    
    
    ########### Properties
    
    @property
    def splitted(self):
        '''The splitted flag indicates whether a sublocus has already been processed to produce the necessary monosubloci.
        It must be set as a boolean flag (hence why it is coded as a property)'''
        return self.__splitted
    
    @splitted.setter
    def splitted(self,verified):
        if type(verified)!=bool:
            raise TypeError()
        self.__splitted=verified
        
    @property
    def id(self):
        if self.monoexonic is True:
            addendum = "mono"
        else:
            addendum = "multi"
        
        return "{0}.{1}".format(super().id, addendum)
        
        
        