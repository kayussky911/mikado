import sys,os.path
from shanghai_lib.loci_objects.transcript import transcript
from shanghai_lib.scales.assigner import assigner
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from shanghai_lib.loci_objects.monosublocus import monosublocus
from shanghai_lib.loci_objects.abstractlocus import abstractlocus

class locus(monosublocus,abstractlocus):
    
    '''Minimal which inherits from monosublocus. It will define the final loci.''' 
    
    __name__ = "locus"
    
    def __init__(self,transcript_instance: transcript, logger = None):
        self.counter=0
        transcript_instance.attributes["primary"]=True
        super().__init__(transcript_instance, logger=logger)
        self.primary_transcript_id = transcript_instance.id
        
        self.attributes["is_fragment"]=False
    
    def __str__(self, print_cds=True) -> str:
          
        self.feature=self.__name__
        return super().__str__(print_cds=print_cds)
    
    def add_transcript_to_locus(self, transcript_instance):
        '''Loci must be able to add multiple transcripts.'''
        
        if not self.is_alternative_splicing(transcript_instance):
            return
        transcript_instance.attributes["primary"]=False
        
        abstractlocus.add_transcript_to_locus(self, transcript_instance)
    
    def other_is_fragment(self,other):
        '''This function checks whether another *monoexonic* locus on the opposite strand* is a fragment, by checking that:
            - there is some overlap between the two transcripts
            - the fragment has 
        
            - the fragment is completely contained inside the coordinates of the other transcript
            - the transcript has at least some exonic overlap and overlaps at most one exon.
        '''

        if type(self)!=type(other):
            raise TypeError("I can compare only loci.")
        
#         self_id = list(self.transcripts.keys())[0]
#         other_id = list(other.transcripts.keys())[0]
        
        #Return
        self.logger.debug( "Comparing {0} with {1}".format(self.primary_transcript_id, other.primary_transcript_id ))
#         if other.strand==self.strand or self.monoexonic is True or other.monoexonic is False:
#             if other.strand == self.strand: self.logger.debug("Same strand for {0} and {1}".format(self_id, other_id))
#             elif self.monoexonic is True: self.logger.debug("{0} is monoexonic".format(self_id))
#             elif other.monoexonic is False: self.logger.debug("{0} is multiexonic".format(other_id))
#             return False
# 
#         #If they do not have overlaps, return False
#         if self.overlap( (other.primary_transcript.start, other.primary_transcript.end), (self.start,self.end))<=0:
#             self.logger.debug( "{0} and {1} do not overlap".format(self_id, other_id) )
#             return False
# #         overlapping_exons=0
#         overlapping_introns=0
#         for intron in self.introns:
#             self.logger.warn("Comparing intron {0} of {1} with ({2},{3})".format(intron, self_id, other.primary_transcript.start, other.primary_transcript.end  ))
#             if self.overlap(intron, (other.start,other.end))>0:
#                 overlapping_introns+=1
#         overlapping_exons=0
#         for exon in self.exons:
#             self.logger.warn("Comparing exon {0} of {1} with ({2},{3})".format(exon, self_id, other.primary_transcript.start, other.primary_transcript.end  ))
#             if self.overlap(exon, (other.start, other.end))>0:
#                 overlapping_exons+=1
#         self.logger.warn("{0} overlaps {1} exons and {2} introns".format(other_id, overlapping_exons, overlapping_introns )  )
#         if 0<overlapping_exons<=2 and overlapping_introns<=1:
#             return True
#         return False
        result, _ = assigner.compare( other.primary_transcript, self.primary_transcript)
        if result.ccode == ("x",) or result.ccode == ("P",):
            return True
        return False

    
    
    def is_alternative_splicing(self, other):
    
        '''This function defines whether another transcript could be a putative alternative splice variant.
        To do so, it compares the candidate against all transcripts in the locus, and calculates
        the class code using scales.assigner.compare.
        If all the matches are "n" or "j", the transcript is considered as an AS event.
        '''
        
        if other.id == self.primary_transcript_id: return False
#         primary = self.transcripts[self.primary_transcript_id]
        if self.overlap((other.start, other.end), (self.start, self.end) ) < 0: return False
        
#         if other.monoexonic != self.monoexonic: return False
        if other.strand != other.strand: return False
        if other.retained_intron_num>0: return False
        
        for tid in self.transcripts:
            result,_ = assigner.compare(other, self.transcripts[tid]) 
            self.logger.debug("{0} vs. {1}: {2}".format(tid, other.id, result.ccode[0]))
            if result.ccode[0] not in ("j", "n"):
                return False
            if result.n_f1==0 or result.j_f1 == 0:
                return False
        
        return True
    
    
    @property
    def id(self):
        Id = abstractlocus.id.fget(self)  # @UndefinedVariable
        if self.counter>0:
            Id = "{0}.{1}".format(Id, self.counter)
        return Id
    
    @property
    def is_fragment(self):
        return self.attributes["is_fragment"]
    
    @is_fragment.setter
    def is_fragment(self, val: bool):
        if not type(val) is bool:
            raise ValueError(val)
        self.attributes["is_fragment"]=val
        
    @property
    def primary_transcript(self):
        return self.transcripts[self.primary_transcript_id]